from werkzeug.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, message, status_code=400, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        body = {"error": err.message}
        if err.details:
            body["details"] = err.details
        return body, err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return {"error": err.description}, err.code
