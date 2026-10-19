package com.acme.billing.payout;

import com.acme.billing.common.Money;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class StripePaymentGateway implements PaymentGateway {

    private static final Logger log = LoggerFactory.getLogger(StripePaymentGateway.class);

    private final RestClient stripeClient;

    public StripePaymentGateway(RestClient stripeClient) {
        this.stripeClient = stripeClient;
    }

    @Override
    public String sendPayout(String merchantId, Money amount) {
        try {
            String reference = this.stripeClient.post().uri("/v1/payouts").body(new PayoutRequest(merchantId, amount))
                    .retrieve().body(String.class);
            log.info("Payout {} sent for merchant {}", reference, merchantId);
            return reference;
        }
        catch (RestClientException ex) {
            throw new PaymentProviderUnavailableException("stripe", ex);
        }
    }

    @Override
    public Money fetchDailyLimit(String merchantId) {
        try {
            return this.stripeClient.get().uri("/v1/merchants/{id}/limit", merchantId).retrieve().body(Money.class);
        }
        catch (RestClientException ex) {
            throw new PaymentProviderUnavailableException("stripe", ex);
        }
    }

    record PayoutRequest(String merchantId, Money amount) {
    }
}
