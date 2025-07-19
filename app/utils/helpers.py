import io
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse


def format_table(data, column_names=None, html_title=None, html_subtitle=None, format="html", dimensions=2, download_filename='table'):
    """
    Format data into a table for different output formats.

    Args:
        data (list): The data to format.
        column_names (list, optional): Column names for the table.
        html_title (str, optional): Title for HTML output.
        html_subtitle (str, optional): Subtitle for HTML output.
        format (str): Output format ('text', 'csv', 'file', 'html').
        dimensions (int): Number of dimensions in the data (1 or 2).
        download_filename (str): Filename for downloadable content.

    Returns:
        Response: Formatted response based on the specified format.
    """
    if format in ["text", "csv", "file"]:
        # Text: comma-separated values, one row per line
        lines = []
        if column_names:
            lines.append(",".join(column_names))
        if dimensions == 1:
            lines.append(",".join(str(item) for item in data))
        else:
            for row in data:
                if format in ["csv", "file"]:
                    lines.append(",".join(f"\"{str(cell)}\"" for cell in row))
                else:
                    lines.append(",".join(str(cell) for cell in row))
        content = "\n".join(lines)
        if format in ["file", "csv"]:
            return StreamingResponse(
                io.StringIO(content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={download_filename}.csv"}
            )
        return PlainTextResponse(content)
    else:
        # HTML: simple table
        html = "<head> <style> table { font-family: arial, sans-serif; border-collapse: collapse; width: 80%; }"
        html += " td, th { border: 1px solid #dddddd; text-align: left; padding: 8px; }"
        html += " tr:nth-child(even) { background-color: #dddddd; } </style> </head>"
        html += "<html><body>"
        if html_title:
            html += f"<h2>{html_title}</h2>"
        if html_subtitle:
            html += f"<h4>{html_subtitle}</h4>"
        html += "<table border='1'>"
        if column_names:
            html += "<tr>" + "".join(f"<th>{col}</th>" for col in column_names) + "</tr>"
        if dimensions == 1:
            html += "<ul>"
            html += "".join(f"<li>{item}</li>" for item in data)
            html += "</ul>"
        else:
            for row in data:
                html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        html += "</table></body></html>"
        return HTMLResponse(html)
