class NotInitializedStorageError(Exception):
    """
    This exception is raised if the user attempts to read an UploadSet config
    without calling the init_app method of the extension first.
    """


class NotFoundDestinationError(Exception):
    """
    This exception is raised if a destination cannot be found for a given UploadSet
    """


class NotFoundUploadSetError(Exception):
    """
    This exception is raised is the user attempts to read an UploadSet config
    that was not configured in the current application context
    """


class NotAllowedUploadError(Exception):
    """
    This exception is raised if the upload was not allowed. You should catch
    it in your view code and display an appropriate message to the user.
    """
