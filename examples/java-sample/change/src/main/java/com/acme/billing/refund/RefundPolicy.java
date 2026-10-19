package com.acme.billing.refund;

public interface RefundPolicy {

    boolean isRefundable(String invoiceId);
}
