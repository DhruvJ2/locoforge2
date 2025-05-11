"""Node definitions for the agent graph."""

from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import os
import json
import logging
import asyncio
from functools import partial
import sqlite3
from contextlib import contextmanager
from .state import InputState, Configuration
from .sql_agent import SQLAgent
from agent.utils.logger import setup_logger
from agent.utils.no_sql_agent import GeneralizedNoSQLAgent, MongoJSONEncoder

logger = logging.getLogger(__name__)


def get_llm(config: Configuration) -> ChatOpenAI:
    """Initialize and return the LLM with configuration."""
    return ChatOpenAI(
        model=config.get("model_name", "gpt-3.5-turbo"),
        temperature=config.get("temperature", 0.7),
        api_key=os.getenv("OPENAI_API_KEY")
    )


@contextmanager
def get_sqlite_connection(db_path: str):
    """Context manager for SQLite connections."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_table_schema(db_path: str) -> str:
    """Get the schema of the database tables."""
    with get_sqlite_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        schemas = cursor.fetchall()
        return "\n".join([schema[0] for schema in schemas])


def get_mongo_schema() -> Dict[str, Any]:
    """Get MongoDB schema in a thread-safe way."""
    try:
        nosql_agent = GeneralizedNoSQLAgent()
        available_dbs = nosql_agent.list_databases()
        
        if available_dbs:
            db_name = available_dbs[0]
        else:
            db_name = "user_management_db"
            
        nosql_agent.use_database(db_name)
        schemas = nosql_agent.get_all_schemas()
        nosql_agent.close()
        return schemas
    except Exception as e:
        logger.error(f"Error getting MongoDB schema: {str(e)}", exc_info=True)
        return {}


async def get_schema_context():
    """Get the schema context from both SQL and NoSQL databases."""
    try:
        # Get SQL schema
        db_path = os.path.join(os.path.dirname(__file__), "sales.db")
        logger.info(f"Attempting to connect to SQL database at: {db_path}")
        
        # Get SQL schema in a thread-safe way
        sql_schema = await asyncio.to_thread(get_table_schema, db_path)

        # Get MongoDB schema in a thread-safe way
        logger.info("Attempting to connect to MongoDB")
        nosql_schemas = await asyncio.to_thread(get_mongo_schema)

        return {
            "sql_schema": sql_schema,
            "nosql_schemas": nosql_schemas
        }
    except Exception as e:
        logger.error(f"Error getting schema context: {str(e)}", exc_info=True)
        return {
            "sql_schema": "Error retrieving SQL schema",
            "nosql_schemas": "Error retrieving NoSQL schemas",
            "error": str(e)
        }


async def supervisor_node(state: InputState, config: RunnableConfig) -> Dict[str, Any]:
    """Supervisor node that analyzes user query and creates structured tasks for agents."""
    try:
        # Get the last message and schema context
        last_message = state["messages"][-1]["content"]
        schema_context = await get_schema_context()
        
        # Create a prompt for the LLM to analyze the query and create structured tasks
        system_prompt = f"""You are a smart data analysis expert. Analyze the user's query and determine what data needs to be gathered from SQL and NoSQL databases.

Available Database Schemas:
SQL Schema:
{schema_context.get('sql_schema', 'No SQL schema available')}

NoSQL Schema:
{schema_context.get('nosql_schemas', 'No NoSQL schema available')}

User Query: {last_message}

Your task is to:
1. Analyze the query to determine if it requires data from SQL, NoSQL, or both databases
2. Create appropriate tasks for each required database type
3. For taskDefinition about "all tables" or "all data", you MUST create tasks for both SQL and NoSQL databases
4. Assign priorities based on the logical order of operations (e.g., if NoSQL data depends on SQL data, SQL task gets higher priority)

Respond with a JSON object in this format:
{{
    "tasks": [
        {{
            "agent": "sql_agent" or "nosql_agent" or "drive_agent",
            "taskDefinition": "a clear description of the task for which a query is needed",
            "purpose": "brief explanation of why this query is needed",
            "priority": 1-5,  # Higher number means higher priority
            "dependencies": ["list of task indices this task depends on"]
        }}
    ],
    "context": {{
        "required_data": ["list of data points needed"],
        "relationships": ["how the data points relate to each other"],
        "error_handling": {{
            "retry_count": 3,
            "fallback_strategy": "description of fallback approach"
        }}
    }}
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": last_message}
        ]
        
        # Initialize LLM with config
        llm = get_llm(config)
        
        # Move LLM call to a separate thread
        response = await asyncio.to_thread(llm.invoke, messages)
        task_analysis = json.loads(response.content)
        
        # Sort tasks by priority
        sorted_tasks = sorted(task_analysis["tasks"], key=lambda x: x["priority"], reverse=True)
        
        # Create the output state with messages
        output_state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "tasks": sorted_tasks,  # Return all tasks, not just the first one
                        "context": task_analysis["context"],
                        "current_task_index": 0,  # Start with the first task
                        "error_handling": task_analysis["context"]["error_handling"],
                        "analysis": {
                            "total_tasks": len(sorted_tasks),
                            "task_types": list(set(task["agent"] for task in sorted_tasks)),
                            "highest_priority_task": sorted_tasks[0] if sorted_tasks else None
                        }
                    }, indent=2)
                }
            ]
        }
        
        return output_state
    except Exception as e:
        logger.error(f"Error in supervisor_node: {str(e)}", exc_info=True)
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "status": "error",
                        "error": f"Failed to analyze query: {str(e)}",
                        "retry_count": 0
                    }, indent=2)
                }
            ]
        }


async def sql_agent_node(state: InputState, config: RunnableConfig) -> Dict[str, Any]:
    """SQL agent node that processes SQL-related tasks from the supervisor."""
    try:
        # Get the last message which contains the task analysis
        last_message = state["messages"][-1]["content"]
        task_analysis = json.loads(last_message)
        
        # Initialize SQL agent
        db_path = os.path.join(os.path.dirname(__file__), "sales.db")
        sql_agent = SQLAgent(db_path)
        
        # Find SQL tasks
        sql_tasks = [task for task in task_analysis["tasks"] if task["agent"] == "sql_agent"]
        
        results = []
        for task in sql_tasks:
            try:
                # Execute the SQL task and await the result
                result = await sql_agent.execute_query(task["taskDefinition"])
                # Ensure the result is a dictionary, not a coroutine
                if isinstance(result, dict):
                    results.append({
                        "task": task,
                        "result": result
                    })
                else:
                    logger.error(f"Unexpected result type: {type(result)}")
                    results.append({
                        "task": task,
                        "error": "Invalid result type from SQL agent"
                    })
            except Exception as e:
                logger.error(f"Error executing SQL task: {str(e)}", exc_info=True)
                results.append({
                    "task": task,
                    "error": str(e)
                })
        
        # Close the SQL agent connection
        sql_agent.close()
        
        # Create the output state with results
        output_state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "status": "success",
                        "sql_results": results,
                        "original_analysis": task_analysis
                    }, indent=2)
                }
            ]
        }
        
        return output_state
    except Exception as e:
        logger.error(f"Error in sql_agent_node: {str(e)}", exc_info=True)
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "status": "error",
                        "error": f"Failed to process SQL tasks: {str(e)}",
                        "retry_count": 0
                    }, indent=2)
                }
            ]
        }

# Initialize logger
logger = setup_logger('nosql_agent_node')

async def nosql_agent_node(state: InputState, config: RunnableConfig) -> Dict[str, Any]:
    """NoSQL agent node that processes NoSQL-related tasks from the supervisor."""
    try:
        # Get the last message which contains the task analysis
        last_message = state["messages"][-1]["content"]
        task_analysis = json.loads(last_message)
        
        # Initialize NoSQL agent using the GeneralizedNoSQLAgent class
        nosql_connection_string = os.getenv("NOSQL_CONNECTION_STRING", "mongodb://localhost:27017")
        database_name = os.getenv("NOSQL_DATABASE", "user_management_db")
        nosql_agent = GeneralizedNoSQLAgent(nosql_connection_string, database_name)
        
        # Find NoSQL tasks
        nosql_tasks = [task for task in task_analysis["tasks"] if task["agent"] == "nosql_agent"]
        
        results = []
        for task in nosql_tasks:
            try:
                # Execute the NoSQL task
                result = nosql_agent.execute_query(task["taskDefinition"])
                
                # Ensure the result is a dictionary
                if isinstance(result, dict):
                    # Convert to JSON serializable format using MongoJSONEncoder
                    result_str = json.dumps(result, cls=MongoJSONEncoder)
                    result_dict = json.loads(result_str)
                    
                    results.append({
                        "task": task,
                        "result": result_dict
                    })
                else:
                    logger.error(f"Unexpected result type: {type(result)}")
                    results.append({
                        "task": task,
                        "error": "Invalid result type from NoSQL agent"
                    })
            except Exception as e:
                logger.error(f"Error executing NoSQL task: {str(e)}", exc_info=True)
                results.append({
                    "task": task,
                    "error": str(e)
                })
        
        nosql_agent.close()
        
        # Create the output state with results
        output_state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "status": "success",
                        "nosql_results": results,
                        "original_analysis": task_analysis
                    }, indent=2)
                }
            ]
        }
        
        return output_state
    except Exception as e:
        logger.error(f"Error in nosql_agent_node: {str(e)}", exc_info=True)
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "status": "error",
                        "error": f"Failed to process NoSQL tasks: {str(e)}",
                        "retry_count": 0
                    }, indent=2)
                }
            ]
        }