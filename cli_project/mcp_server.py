from mcp.server.fastmcp import FastMCP
from pydantic import Field
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("DocumentMCP", log_level="ERROR")

docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}


@mcp.tool(name="read_document", description="Read the contents of a document by its ID.")
def read_document(doc_id: str = Field(description="ID of the document")):
    if doc_id not in docs:
        raise ValueError(f"Document with id '{doc_id}' not found.")
    return docs[doc_id]


@mcp.tool(name="edit_document", description="Edit the contents of a document by its ID.")
def edit_document(
    doc_id: str = Field(description="ID of the document to edit"),
    content: str = Field(description="New content for the document"),
):
    if doc_id not in docs:
        raise ValueError(f"Document with id '{doc_id}' not found.")
    docs[doc_id] = content
    return f"Document '{doc_id}' updated successfully."


@mcp.resource("docs://documents", mime_type="application/json")
def list_documents():
    return list(docs.keys())


@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")
def get_document(doc_id: str):
    if doc_id not in docs:
        raise ValueError(f"Document with id '{doc_id}' not found.")
    return docs[doc_id]


@mcp.prompt(name="format", description="Rewrite a document using Markdown formatting.")
def format_document(
    doc_id: str = Field(description="ID of the document to format"),
) -> list[base.Message]:
    prompt = f"""Your goal is to reformat a document using Markdown syntax.

The ID of the document you need to reformat is:
<document_id>
{doc_id}
</document_id>

Add headers, bullet points, tables, and other Markdown elements as appropriate.
"""
    return [base.UserMessage(prompt)]


@mcp.prompt(name="summarize", description="Summarize a document concisely.")
def summarize_document(
    doc_id: str = Field(description="ID of the document to summarize"),
) -> list[base.Message]:
    prompt = f"""Your goal is to produce a concise summary of a document.

The ID of the document you need to summarize is:
<document_id>
{doc_id}
</document_id>

Provide a brief summary covering the key points. Keep it to 3-5 sentences.
"""
    return [base.UserMessage(prompt)]


if __name__ == "__main__":
    mcp.run(transport="stdio")
