package com.acme.billing.invoice;

import com.acme.billing.common.Money;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class InvoiceServiceTests {

    private final Clock clock = Clock.fixed(Instant.parse("2026-01-01T00:00:00Z"), ZoneOffset.UTC);

    @Mock
    private InvoiceRepository invoiceRepository;

    @Test
    void shouldMarkOpenInvoicePaid() {
        Invoice invoice = new Invoice("inv-1", Money.of("10.00", "EUR"));
        given(this.invoiceRepository.findById("inv-1")).willReturn(Optional.of(invoice));

        Invoice result = new InvoiceService(this.invoiceRepository, this.clock).markInvoicePaid("inv-1");

        assertThat(result.isPaid()).isTrue();
        assertThat(result.paidAt()).isEqualTo(Instant.parse("2026-01-01T00:00:00Z"));
    }

    @Test
    void shouldRejectUnknownInvoice() {
        given(this.invoiceRepository.findById("missing")).willReturn(Optional.empty());

        assertThatThrownBy(() -> new InvoiceService(this.invoiceRepository, this.clock).markInvoicePaid("missing"))
                .isInstanceOf(InvoiceNotFoundException.class)
                .hasMessageContaining("missing");
    }
}
