from django.http import HttpResponse
import traceback
import sys


def handler500(request):
    """Custom 500 error handler to show debug info"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    html = f"""
    <html>
    <head><title>Error 500</title></head>
    <body>
        <h1>Internal Server Error</h1>
        <pre style="background: #f4f4f4; padding: 20px; overflow: auto;">
{error_message}
        </pre>
    </body>
    </html>
    """
    return HttpResponse(html, status=500)
