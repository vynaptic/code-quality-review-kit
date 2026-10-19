package com.acme.billing.common;

/** Stable error codes exposed to API clients. */
public enum ErrorCode {
    INVOICE_NOT_FOUND(404),
    INVOICE_ALREADY_PAID(409),
    PAYOUT_LIMIT_EXCEEDED(422),
    PAYMENT_PROVIDER_UNAVAILABLE(503);

    private final int httpStatus;

    ErrorCode(int httpStatus) {
        this.httpStatus = httpStatus;
    }

    public int httpStatus() {
        return this.httpStatus;
    }
}
