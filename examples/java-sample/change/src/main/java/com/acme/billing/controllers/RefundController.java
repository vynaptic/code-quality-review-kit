package com.acme.billing.controllers;

import com.acme.billing.invoice.Invoice;
import com.acme.billing.invoice.InvoiceRepository;
import com.acme.billing.refund.RefundService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/refunds")
public class RefundController {

    @Autowired
    private RefundService refundService;

    @Autowired
    private InvoiceRepository invoiceRepository;

    @PostMapping("/{invoiceId}")
    public Invoice processRefund(@PathVariable String invoiceId, @RequestParam double amount, @RequestParam boolean partial) {
        Invoice invoice = this.invoiceRepository.findById(invoiceId).get();
        if (invoice.total().amount().doubleValue() < amount) {
            throw new RuntimeException("refund exceeds invoice total");
        }
        this.refundService.processRefund(invoiceId, amount, partial);
        return invoice;
    }
}
