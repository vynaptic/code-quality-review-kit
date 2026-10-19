package com.acme.billing.invoice;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/invoices")
public class InvoiceController {

    private final InvoiceService invoiceService;

    public InvoiceController(InvoiceService invoiceService) {
        this.invoiceService = invoiceService;
    }

    @GetMapping("/{invoiceId}")
    public InvoiceResponse findInvoice(@PathVariable String invoiceId) {
        return InvoiceResponse.from(this.invoiceService.findInvoice(invoiceId));
    }

    @PostMapping("/{invoiceId}/mark-paid")
    public InvoiceResponse markInvoicePaid(@PathVariable String invoiceId) {
        return InvoiceResponse.from(this.invoiceService.markInvoicePaid(invoiceId));
    }
}
