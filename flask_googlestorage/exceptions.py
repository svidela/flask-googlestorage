class NotFoundDestinationError(Exception):
    """
    This exception is raised if the ``GOOGLE_STORAGE_LOCAL_DEST`` configuration variable is unset
    """


class NotFoundBucketError(Exception):
    """
    This exception is raised is the user reads a bucket not configured in the current application
    """


class NotAllowedUploadError(Exception):
    """
    This exception is raised if the upload file is not allowed in the bucket.
    """
