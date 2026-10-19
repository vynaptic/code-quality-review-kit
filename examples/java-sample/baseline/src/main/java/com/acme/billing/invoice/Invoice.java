package com.acme.billing.invoice;

import com.acme.billing.common.Money;
import java.time.Instant;
import java.util.Objects;

/** Aggregate root for an invoice; state transitions are methods, not setters. */
public class Invoice {

    public enum Status { OPEN, PAID, CANCELLED }

    private final String id;
    private final Money total;
    private Status status;
    private Instant paidAt;

    public Invoice(String id, Money total) {
        this.id = Objects.requireNonNull(id, "id must not be null");
        this.total = Objects.requireNonNull(total, "total must not be null");
        this.status = Status.OPEN;
    }

    public void markPaid(Instant at) {
        if (this.status != Status.OPEN) {
            throw new InvoiceAlreadyPaidException(this.id);
        }
        this.status = Status.PAID;
        this.paidAt = at;
    }

    public boolean isPaid() {
        return this.status == Status.PAID;
    }

    public String id() {
        return this.id;
    }

    public Money total() {
        return this.total;
    }

    public Status status() {
        return this.status;
    }

    public Instant paidAt() {
        return this.paidAt;
    }
}
