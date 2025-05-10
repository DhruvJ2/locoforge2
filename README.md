# Database Connector Agent System

A modular AI-powered database connector system that translates natural language queries into database operations using LangChain and LangGraph.

## Development Environment

This project uses LangGraph Studio for development, visualization, and debugging of the agent workflows. LangGraph Studio provides:

- Visual representation of agent workflows
- Real-time debugging and monitoring
- Interactive testing of agent chains
- Performance metrics and analytics
- Easy workflow modification and iteration

To use LangGraph Studio:

1. Install LangGraph Studio: `pip install langgraph-studio`
2. Start the studio: `langgraph-studio`
3. Access the web interface at `http://localhost:3000`

## Architecture Overview

The system follows a modular architecture with the following components:

1. **Core Components**

   - Supervisor Agent: Orchestrates the query processing and task distribution
   - Database Agents: Specialized agents for different database types (SQL, NoSQL)
   - LLM (ChatGPT) for natural language understanding and query translation
   - LangGraph for orchestrating the agent pipeline
   - Modular database connectors (SQL, MongoDB, Google Drive)

2. **System Flow**
   ```
   User Query → Supervisor Agent → Database Context Collection → Task Distribution →
   Database Agents → Data Collection → Response Aggregation → User Response
   ```

## Detailed Implementation Plan

### Phase 1: Project Setup and Environment

1. Initialize project structure

   ```
   /src
     /agents
       supervisor_agent.py
       sql_agent.py
       nosql_agent.py
     /connectors
       sql_connector.py
       nosql_connector.py
     /utils
       context_collector.py
       response_formatter.py
     /config
       settings.py
     /workflows
       supervisor_workflow.py
       sql_workflow.py
       nosql_workflow.py
   ```

2. Set up virtual environment and dependencies
   - langchain
   - langgraph
   - langgraph-studio
   - openai
   - sqlalchemy
   - pymongo
   - python-dotenv

### Phase 2: Core Components Implementation

1. **Supervisor Agent**

   - Natural language query understanding
   - Database context collection
   - Task distribution logic
   - Response aggregation
   - Error handling and retry mechanisms
   - LangGraph Studio workflow visualization and debugging

2. **Database Context Collector**

   - SQL database schema collection
   - NoSQL collection structure analysis
   - Table/collection relationship mapping
   - Metadata storage and caching

3. **Task Distribution System**
   - Task creation based on query analysis
   - Priority assignment
   - Parallel execution management
   - Result aggregation

### Phase 3: Database Agents Implementation

1. **SQL Agent**

   - Schema understanding
   - Query generation
   - Result formatting
   - Error handling
   - Performance optimization

2. **NoSQL Agent**
   - Collection structure analysis
   - Query translation
   - Result aggregation
   - Error handling
   - Performance optimization

### Phase 4: Connector Implementation

1. **SQL Connector**

   - Connection pooling
   - Query execution
   - Result formatting
   - Transaction management
   - Error handling

2. **NoSQL Connector**
   - Connection management
   - Query execution
   - Result formatting
   - Error handling
   - Performance optimization

### Phase 5: Integration and Testing

1. **Unit Tests**

   - Agent functionality tests
   - Connector tests
   - Context collector tests
   - Response formatter tests

2. **Integration Tests**

   - End-to-end query processing
   - Multi-database scenarios
   - Error handling scenarios
   - Performance testing

3. **System Tests**
   - Load testing
   - Concurrent query handling
   - Resource utilization
   - Error recovery

### Phase 6: Documentation and Deployment

1. **Documentation**

   - API documentation
   - Setup guide
   - Usage examples
   - Troubleshooting guide

2. **Deployment**
   - Docker containerization
   - Environment configuration
   - Monitoring setup
   - Logging implementation

## Example Usage

```python
# Example query flow using LangGraph Studio
from langgraph.studio import Studio

# Initialize LangGraph Studio
studio = Studio()

# Create and visualize the workflow
workflow = studio.create_workflow("database_query_workflow")

# Define the workflow steps
workflow.add_node("supervisor", SupervisorAgent())
workflow.add_node("sql_agent", SQLAgent())
workflow.add_node("nosql_agent", NoSQLAgent())

# Connect the nodes
workflow.add_edge("supervisor", "sql_agent")
workflow.add_edge("supervisor", "nosql_agent")

# Example query
user_query = "what are all the data we are saving give a summary"

# Execute and visualize the workflow
results = workflow.execute(user_query)
```

## Getting Started

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Set up environment variables in `.env`
5. Run the development server: `python src/main.py`

## Environment Variables

```
OPENAI_API_KEY=your_api_key
SQL_DATABASE_URL=your_sql_connection_string
NOSQL_DATABASE_URL=your_nosql_connection_string
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
# locoforge2
