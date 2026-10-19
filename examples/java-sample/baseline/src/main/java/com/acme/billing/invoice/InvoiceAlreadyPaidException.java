package com.acme.billing.invoice;

import com.acme.billing.common.BillingException;
import com.acme.billing.common.ErrorCode;

public class InvoiceAlreadyPaidException extends BillingException {

    public InvoiceAlreadyPaidException(String invoiceId) {
        super(ErrorCode.INVOICE_ALREADY_PAID, "Invoice " + invoiceId + " is already paid");
    }
}
