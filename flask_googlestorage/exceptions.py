class NotFoundDestinationError(Exception):
    """
    This exception is raised if a destination cannot be found for a given UploadSet
    """


class NotFoundBucketError(Exception):
    """
    This exception is raised is the user attempts to read a bucket config
    that was not configured in the current application context
    """


class NotAllowedUploadError(Exception):
    """
    This exception is raised if the upload was not allowed. You should catch
    it in your view code and display an appropriate message to the user.
    """
