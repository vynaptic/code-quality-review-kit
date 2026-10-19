package com.acme.billing.refund;

import org.springframework.stereotype.Component;

@Component
public class DefaultRefundPolicy implements RefundPolicy {

    @Override
    public boolean isRefundable(String invoiceId) {
        return invoiceId != null && !invoiceId.isBlank();
    }
}
