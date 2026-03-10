"""
SQL Generation – SQL Prompt Builder
Build prompt chuẩn 6-block cho LLM sinh SQL.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SQL_PROMPT_TEMPLATE = """You are an expert SQL generator for a banking database.

Your task is to write a valid SQL query based on the user question.

You MUST follow these rules:

1. Use ONLY the tables and columns provided in the schema.
2. Do NOT invent tables or columns.
3. Use entities provided in the entity list.
4. The SQL must be syntactically valid.
5. Only generate a SELECT query.
6. Limit the result to {row_limit} rows.

---------------------
DATABASE SCHEMA
{schema_description}

---------------------
USER QUESTION
{question}

---------------------
INTENT
{intent_name}

INTENT DESCRIPTION
{intent_description}

---------------------
EXTRACTED ENTITIES
{entities_json}

---------------------
TEMPLATE HINT
{template_sql}

---------------------
Write the final SQL query.

Return ONLY the SQL query."""


def build_sql_prompt(
    question: str,
    schema_description: str,
    intent_name: str = "",
    intent_description: str = "",
    entities: Optional[Dict[str, str]] = None,
    template_sql: str = "",
    row_limit: int = 100,
) -> str:
    """
    Build prompt chuẩn 6-block cho LLM.
    """
    entities_json = json.dumps(entities or {}, ensure_ascii=False, indent=2)

    prompt = SQL_PROMPT_TEMPLATE.format(
        schema_description=schema_description,
        question=question,
        intent_name=intent_name,
        intent_description=intent_description,
        entities_json=entities_json,
        template_sql=template_sql or "No template available.",
        row_limit=row_limit,
    )

    logger.info(f"[Prompt] Built prompt ({len(prompt)} chars)")
    return prompt


RETRY_SYNTAX_PROMPT = """The following SQL has a syntax error.

SQL:
{sql}

Error:
{error_message}

Fix the SQL query using the same schema.
Return only corrected SQL."""


RETRY_SCHEMA_PROMPT = """The SQL query used invalid table or column names.

Available schema:
{schema}

Original SQL:
{sql}

Error:
{error_message}

Fix the query using only available tables and columns.
Return only corrected SQL."""


RETRY_LOGIC_PROMPT = """The SQL returned no result.

User question:
{question}

Schema:
{schema}

Previous SQL:
{sql}

Try a different approach to answer the question.
Return only SQL."""


def build_retry_prompt(
    retry_type: str,
    sql: str,
    error_message: str = "",
    schema: str = "",
    question: str = "",
) -> str:
    """
    Build retry prompt theo loại lỗi.
    retry_type: "syntax" | "schema" | "logic"
    """
    if retry_type == "syntax":
        return RETRY_SYNTAX_PROMPT.format(sql=sql, error_message=error_message)
    elif retry_type == "schema":
        return RETRY_SCHEMA_PROMPT.format(
            schema=schema, sql=sql, error_message=error_message
        )
    elif retry_type == "logic":
        return RETRY_LOGIC_PROMPT.format(
            question=question, schema=schema, sql=sql
        )
    else:
        return RETRY_SYNTAX_PROMPT.format(sql=sql, error_message=error_message)
