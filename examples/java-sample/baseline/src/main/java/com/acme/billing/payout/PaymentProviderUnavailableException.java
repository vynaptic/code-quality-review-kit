package com.acme.billing.payout;

import com.acme.billing.common.BillingException;
import com.acme.billing.common.ErrorCode;

public class PaymentProviderUnavailableException extends BillingException {

    public PaymentProviderUnavailableException(String provider, Throwable cause) {
        super(ErrorCode.PAYMENT_PROVIDER_UNAVAILABLE, "Payment provider " + provider + " is unavailable", cause);
    }
}
