package com.acme.billing.payout;

import com.acme.billing.common.BillingException;
import com.acme.billing.common.ErrorCode;
import com.acme.billing.common.Money;

public class PayoutLimitExceededException extends BillingException {

    public PayoutLimitExceededException(String merchantId, Money requested, Money limit) {
        super(ErrorCode.PAYOUT_LIMIT_EXCEEDED,
                "Payout of " + requested + " for merchant " + merchantId + " exceeds the daily limit " + limit);
    }
}
