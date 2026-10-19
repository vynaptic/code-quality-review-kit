package com.acme.billing.common;

/**
 * Root of all billing domain errors. Carries a stable {@link ErrorCode} that the
 * {@code GlobalExceptionHandler} maps to an HTTP status and problem body.
 *
 * <p>Subclasses are immutable and name the problem, not the operation.
 */
public abstract class BillingException extends RuntimeException {

    private final ErrorCode errorCode;

    protected BillingException(ErrorCode errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    protected BillingException(ErrorCode errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public ErrorCode getErrorCode() {
        return this.errorCode;
    }
}
