package com.acme.billing.invoice;

import com.acme.billing.common.BillingException;
import com.acme.billing.common.ErrorCode;

public class InvoiceNotFoundException extends BillingException {

    public InvoiceNotFoundException(String invoiceId) {
        super(ErrorCode.INVOICE_NOT_FOUND, "Invoice " + invoiceId + " does not exist");
    }
}
