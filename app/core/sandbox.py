import httpx

PISTON_API_URL = "https://emkc.org/api/v2/piston"

async def execute_code(code: str, language: str = "python"):
    """
    Executes code safely using Piston API.
    """
    payload = {
        "language": language,
        "version": "*",
        "files": [{"content": code}]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{PISTON_API_URL}/execute", json=payload, timeout=10.0)
            result = response.json()
            
            if "run" in result:
                output = result["run"].get("stdout", "") + result["run"].get("stderr", "")
                return output.strip()
            return "Error: Could not execute code."
            
        except Exception as e:
            return f"Execution failed: {str(e)}"