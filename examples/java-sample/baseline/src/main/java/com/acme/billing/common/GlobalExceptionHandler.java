package com.acme.billing.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** Translates {@link BillingException}s into RFC 7807 problem bodies. */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BillingException.class)
    public ProblemDetail handleBillingException(BillingException ex) {
        log.warn("Billing error {}: {}", ex.getErrorCode(), ex.getMessage());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.valueOf(ex.getErrorCode().httpStatus()), ex.getMessage());
        problem.setProperty("code", ex.getErrorCode().name());
        return problem;
    }
}
