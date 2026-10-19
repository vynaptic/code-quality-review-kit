package com.acme.billing.invoice;

import java.math.BigDecimal;
import java.time.Instant;

/** API representation of an invoice; the entity is never serialised directly. */
public record InvoiceResponse(String id, BigDecimal total, String currency, String status, Instant paidAt) {

    static InvoiceResponse from(Invoice invoice) {
        return new InvoiceResponse(invoice.id(), invoice.total().amount(), invoice.total().currency().getCurrencyCode(),
                invoice.status().name(), invoice.paidAt());
    }
}
