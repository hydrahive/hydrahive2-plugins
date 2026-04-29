"""request — HTTP Request Tool für HydraHive2."""
import asyncio
import json
import time
from urllib.parse import urlparse

from hydrahive.tools.base import Tool, ToolContext, ToolResult


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    url = args.get("url", "")
    method = args.get("method", "GET").upper()
    headers = args.get("headers", {})
    body = args.get("body", None)
    timeout = int(args.get("timeout", 10))
    
    if not url:
        return ToolResult.fail("URL ist erforderlich")
    
    # Basic URL validation
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            return ToolResult.fail("Ungültige URL: fehlendes Protokoll (http/https)")
    except Exception as e:
        return ToolResult.fail(f"Ungültige URL: {e}")
    
    start_time = time.time()
    
    try:
        # Use asyncio subprocess for curl (more reliable than aiohttp)
        cmd = ["curl", "-s", "-w", "\n%{http_code}|%{time_total}", 
               "-X", method, "-H", f"Content-Type: application/json"]
        
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
        
        if body:
            cmd.extend(["-d", json.dumps(body)])
        
        cmd.append(url)
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = time.time() - start_time
        
        output = stdout.decode().strip()
        
        # Parse response and status code
        if "|" in output:
            response_body, status_info = output.rsplit("|", 1)
            status_code = status_info.split("|")[0] if "|" in status_info else "000"
            time_total = float(status_info.split("|")[1]) if "|" in status_info else elapsed
        else:
            response_body = output
            status_code = "000"
        
        # Try to parse JSON
        json_body = None
        try:
            json_body = json.loads(response_body) if response_body else None
        except json.JSONDecodeError:
            pass
        
        return ToolResult.ok({
            "url": url,
            "method": method,
            "status_code": int(status_code) if status_code.isdigit() else 0,
            "elapsed_ms": round(elapsed * 1000, 2),
            "time_total_s": round(elapsed, 3),
            "body": json_body if json_body is not None else response_body,
            "body_raw": response_body[:1000] if response_body else "",
            "success": 200 <= int(status_code) < 300 if status_code.isdigit() else False,
            "error": stderr.decode() if stderr else None,
        })
        
    except asyncio.TimeoutError:
        return ToolResult.fail(f"Timeout nach {timeout}s")
    except Exception as e:
        return ToolResult.fail(f"Request fehlgeschlagen: {str(e)}")


TOOL = Tool(
    name="request",
    description="Führt HTTP Request aus (GET/POST/PUT/DELETE). Gibt Status, Response-Body und Zeit zurück.",
    schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL für den Request",
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP Methode (default: GET)",
            },
            "headers": {
                "type": "object",
                "description": "Optionale Headers als JSON",
            },
            "body": {
                "type": "object",
                "description": "Request Body für POST/PUT (wird als JSON gesendet)",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in Sekunden (default: 10)",
            },
        },
        "required": ["url"],
    },
    execute=_execute,
)
