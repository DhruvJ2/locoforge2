import sqlite3
from typing import Dict, Any
from agent.utils.llm_config import llm
from agent.utils.logger import default_logger as logger
import asyncio
from contextlib import contextmanager

class SQLAgent:
    def __init__(self, db_path: str):
        self.db_path = db_path
        logger.info(f"Initializing SQLAgent with database: {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Create a new connection for each operation."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _is_read_query(self, sql: str) -> bool:
        """Determine if a query is read-only."""
        normalized_sql = sql.strip().upper()
        return (normalized_sql.startswith("SELECT") or 
                normalized_sql.startswith("PRAGMA") or
                normalized_sql.startswith("EXPLAIN"))
        
    async def _get_table_schema(self) -> str:
        """Get the schema of the database tables."""
        logger.debug("Fetching database schema")
        
        def _fetch_schema():
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                schemas = cursor.fetchall()
                return "\n".join([schema[0] for schema in schemas])
            
        return await asyncio.to_thread(_fetch_schema)
    
    async def _generate_sql_query(self, prompt: str) -> str:
        """Generate SQL query using LLM based on the prompt and schema."""
        logger.debug(f"Generating SQL query for prompt: {prompt}")
        schema = await self._get_table_schema()
        system_prompt = f"""You are a SQL expert. Given the following database schema:
        {schema}
        
        Generate a valid SQL query based on the user's request. Only return the SQL query without any explanation.
        The query should be compatible with SQLite syntax.
        For date fields, use the format 'YYYY-MM-DD'.
        Make sure to properly escape string values and handle NULL values appropriately."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await asyncio.to_thread(llm.invoke, messages)
        generated_query = response.content.strip()
        logger.debug(f"Generated SQL query: {generated_query}")
        return generated_query
    
    async def execute_query(self, prompt: str) -> Dict[str, Any]:
        """Execute a query based on the natural language prompt."""
        try:
            logger.info(f"Executing query for prompt: {prompt}")
            # Generate SQL query from the prompt
            sql_query = await self._generate_sql_query(prompt)
            
            def _execute_and_fetch():
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    # Execute the query
                    cursor.execute(sql_query)
                    
                    # Handle different types of queries
                    if sql_query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                        results = cursor.fetchall()
                        columns = [description[0] for description in cursor.description]
                        logger.info(f"Query executed successfully. Retrieved {len(results)} rows")
                        return {
                            "status": "success",
                            "query": sql_query,
                            "results": [dict(zip(columns, row)) for row in results]
                        }
                    else:
                        # For INSERT, UPDATE, DELETE operations
                        conn.commit()
                        logger.info(f"Query executed successfully. Rows affected: {cursor.rowcount}")
                        return {
                            "status": "success",
                            "query": sql_query,
                            "message": f"Query executed successfully. Rows affected: {cursor.rowcount}"
                        }
            
            # Run the blocking operation in a thread and await its result
            result = await asyncio.to_thread(_execute_and_fetch)
            return result
                
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "query": sql_query if 'sql_query' in locals() else None,
                "error": str(e)
            }
    
    def close(self):
        """No-op since connections are managed per-query."""
        pass

# async def main():
#     """Main function to demonstrate the SQL agent usage."""
#     try:
#         # Initialize the agent
#         agent = SQLAgent("/Users/yash/Documents/langgraph_as/src/agent/sales.db")
        
#         # Example queries
#         logger.info("Executing example queries")
#         result = await agent.execute_query("Retrieve all customer-related data from the Customers table")
#         print(result)
        
#     except Exception as e:
#         logger.error(f"An error occurred in main: {str(e)}", exc_info=True)
#         print(f"An error occurred: {str(e)}")
#     finally:
#         agent.close()

# if __name__ == "__main__":
#     asyncio.run(main())
