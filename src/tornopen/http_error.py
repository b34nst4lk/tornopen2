from pydantic import ValidationError


class HTTPError(Exception):
    def __init__(self, status_code: int, *, error_type: str, error_message: str):
        """
        Override this to allow for different error attributes to be captured.
        Note that status_code must always be provided
        """
        self.status_code = status_code
        self.error_type = error_type
        self.error_message = error_message

    def dict(self):
        """
        Override this to determine how the dictionary output should look like.
        Note that status_code must always be provided
        """
        return {
            "error": {
                "type": self.error_type,
                "message": self.error_message,
            }
        }

    def __str__(self) -> str:
        return self.error_message


class UnsupportedMediaTypeError(HTTPError):
    """Raised when a handler expects a JSON request body but the request
    Content-Type is not application/json (or no Content-Type is provided
    with a non-empty body)."""

    def __init__(
        self,
        status_code: int = 415,
        *,
        error_type: str = "unsupported_media_type",
        error_message: str = "Content-Type must be application/json",
    ):
        super().__init__(
            status_code,
            error_type=error_type,
            error_message=error_message,
        )


class RequestValidationError(HTTPError):
    """
    This error is raised specifically when the request has failed validation.
    If a `pydantic.ValidationError` is raised instead, the default behavior
    is to return 500 Internal Server Error. This is necessary because validation
    may fail as a result of uses of pydantic that should not be reported back
    to the client.
    """

    def __init__(self, e: ValidationError, *args, **kwargs):
        super().__init__(*args, error_message=str(e), **kwargs)
        self.validation_error = e

    def errors(self):
        return self.validation_error.errors()
