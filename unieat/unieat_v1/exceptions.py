"""
自定义异常类 - 统一异常处理
"""


class UnieatException(Exception):
    """基础异常类"""
    def __init__(self, message, code=None, details=None):
        self.message = message
        self.code = code or "UNIEAT_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(UnieatException):
    """数据验证异常"""
    def __init__(self, message, field=None, details=None):
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class AuthenticationError(UnieatException):
    """认证异常"""
    def __init__(self, message="认证失败", details=None):
        super().__init__(message, code="AUTH_ERROR", details=details)


class PermissionError(UnieatException):
    """权限异常"""
    def __init__(self, message="权限不足", details=None):
        super().__init__(message, code="PERMISSION_ERROR", details=details)


class ResourceNotFoundError(UnieatException):
    """资源未找到异常"""
    def __init__(self, resource_type, resource_id=None, details=None):
        message = f"{resource_type} 未找到"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, code="RESOURCE_NOT_FOUND", details=details)


class BusinessLogicError(UnieatException):
    """业务逻辑异常"""
    def __init__(self, message, code="BUSINESS_ERROR", details=None):
        super().__init__(message, code=code, details=details)


class ExternalServiceError(UnieatException):
    """外部服务异常"""
    def __init__(self, service_name, message=None, details=None):
        message = message or f"{service_name} 服务异常"
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", details=details)


# 微信相关异常
class WechatServiceError(ExternalServiceError):
    """微信服务异常"""
    def __init__(self, message="微信服务异常", details=None):
        super().__init__("微信", message, details)


# 消费记录相关异常
class ConsumptionError(BusinessLogicError):
    """消费记录异常"""
    def __init__(self, message, details=None):
        super().__init__(message, code="CONSUMPTION_ERROR", details=details)


class StallNotOpenError(ConsumptionError):
    """档口未营业异常"""
    def __init__(self, stall_name, details=None):
        message = f"档口 {stall_name} 当前未营业"
        super().__init__(message, details=details)


class InsufficientDataError(ValidationError):
    """数据不足异常"""
    def __init__(self, field, message=None):
        message = message or f"缺少必要字段: {field}"
        super().__init__(message, field=field)


# 文件上传相关异常
class FileUploadError(UnieatException):
    """文件上传异常"""
    def __init__(self, message="文件上传失败", details=None):
        super().__init__(message, code="FILE_UPLOAD_ERROR", details=details)


class InvalidFileTypeError(FileUploadError):
    """无效文件类型异常"""
    def __init__(self, allowed_types=None, details=None):
        message = "不支持的文件类型"
        if allowed_types:
            message += f"，支持的格式: {', '.join(allowed_types)}"
        super().__init__(message, details=details)


class FileSizeExceededError(FileUploadError):
    """文件大小超限异常"""
    def __init__(self, max_size, details=None):
        message = f"文件大小超出限制，最大允许 {max_size}"
        super().__init__(message, details=details)
