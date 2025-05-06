"""Custom exceptions for the Dell AI SDK."""


class DellAIError(Exception):
    """Base exception for all Dell AI SDK exceptions.

    This is the parent class for all exceptions raised by the Dell AI SDK.
    It provides a common type for catching any SDK-specific error.
    """

    def __init__(self, message, original_error=None):
        """Initialize the exception.

        Args:
            message: A descriptive error message.
            original_error: The original exception that caused this error, if any.
        """
        self.original_error = original_error
        super().__init__(message)


class AuthenticationError(DellAIError):
    """Raised when authentication fails.

    This exception is raised in cases such as:
    - Invalid token provided
    - Token has expired
    - User is not authorized to access the requested resource
    - Failed login attempt
    """

    def __init__(self, message, original_error=None):
        """Initialize the authentication error.

        Args:
            message: A descriptive error message about the authentication failure.
            original_error: The original exception that caused this error, if any.
        """
        super().__init__(message, original_error)


class APIError(DellAIError):
    """Raised when the API returns an error.

    This exception is raised when there are issues with the API request such as:
    - Server errors (5xx)
    - Bad requests (4xx, except 404 which uses ResourceNotFoundError)
    - Unexpected response format
    - Network issues
    """

    def __init__(self, message, status_code=None, response=None, original_error=None):
        """Initialize the API error.

        Args:
            message: A descriptive error message.
            status_code: The HTTP status code returned by the API, if applicable.
            response: The raw API response, if available.
            original_error: The original exception that caused this error, if any.
        """
        self.status_code = status_code
        self.response = response
        super().__init__(message, original_error)


class ResourceNotFoundError(DellAIError):
    """Raised when a requested resource is not found.

    This exception is raised when trying to access resources that don't exist, such as:
    - Model IDs that don't exist
    - Platform SKUs that don't exist
    - Any API endpoint that returns a 404 status code
    """

    def __init__(self, resource_type, resource_id, original_error=None):
        """Initialize the resource not found error.

        Args:
            resource_type: The type of resource that was not found (e.g., "model", "platform").
            resource_id: The ID of the resource that was not found.
            original_error: The original exception that caused this error, if any.
        """
        message = f"{resource_type.capitalize()} with ID '{resource_id}' not found"
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, original_error)


class ValidationError(DellAIError):
    """Raised when input validation fails.

    This exception is raised when the provided parameters don't meet requirements, such as:
    - Invalid model ID format
    - Invalid platform SKU format
    - Unsupported deployment engine
    - Invalid number of GPUs or replicas
    - Incompatible model and platform combination
    """

    def __init__(
        self,
        message,
        parameter=None,
        valid_values=None,
        original_error=None,
        config_details=None,
    ):
        """Initialize the validation error.

        Args:
            message: A descriptive error message.
            parameter: The name of the invalid parameter, if applicable.
            valid_values: A list of valid values for the parameter, if applicable.
            original_error: The original exception that caused this error, if any.
            config_details: A dictionary containing configuration details for the model/platform.
        """
        self.parameter = parameter
        self.valid_values = valid_values
        self.config_details = config_details

        # Add parameter and valid values to the message if provided
        full_message = message
        if parameter and valid_values:
            full_message = f"{message} Valid values for '{parameter}': {', '.join(str(v) for v in valid_values)}"
        elif parameter:
            full_message = f"{message} Parameter: '{parameter}'"

        # Add configuration details if provided
        if config_details and config_details.get("valid_configs"):
            full_message += f"\n\nValid configurations for {config_details.get('model_id')} on {config_details.get('platform_id')}:"
            for config in config_details.get("valid_configs", []):
                full_message += f"\n- GPUs: {config.num_gpus}, Max Input Tokens: {config.max_input_tokens}, Max Total Tokens: {config.max_total_tokens}"

        super().__init__(full_message, original_error)


class GatedRepoAccessError(DellAIError):
    """Raised when a user attempts to access a gated repository without permission.

    This exception is raised when:
    - A model repository is gated (access controlled)
    - The user does not have access to the model repository
    - The user needs to request access before being able to download or use the model
    """

    def __init__(self, model_id, original_error=None):
        """Initialize the gated repository access error.

        Args:
            model_id: The ID of the gated repository the user tried to access.
            original_error: The original exception that caused this error, if any.
        """
        message = (
            f"Access denied: '{model_id}' is a gated repository that requires permission. "
            f"Please request access at https://huggingface.co/{model_id}"
        )
        self.model_id = model_id
        super().__init__(message, original_error)
