package com.acme.billing.payout;

import com.acme.billing.common.Money;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class PayoutServiceTests {

    @Mock
    private PaymentGateway paymentGateway;

    @Test
    void shouldSendPayoutWithinLimit() {
        given(this.paymentGateway.fetchDailyLimit("m-1")).willReturn(Money.of("100.00", "EUR"));
        given(this.paymentGateway.sendPayout("m-1", Money.of("40.00", "EUR"))).willReturn("po_123");

        assertThat(new PayoutService(this.paymentGateway).sendPayout("m-1", Money.of("40.00", "EUR"))).isEqualTo("po_123");
    }

    @Test
    void shouldRejectPayoutAboveLimit() {
        given(this.paymentGateway.fetchDailyLimit("m-1")).willReturn(Money.of("100.00", "EUR"));

        assertThatThrownBy(() -> new PayoutService(this.paymentGateway).sendPayout("m-1", Money.of("140.00", "EUR")))
                .isInstanceOf(PayoutLimitExceededException.class);
    }
}
