package com.acme.billing.payout;

import com.acme.billing.common.Money;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PayoutService {

    private static final Logger log = LoggerFactory.getLogger(PayoutService.class);

    private final PaymentGateway paymentGateway;

    public PayoutService(PaymentGateway paymentGateway) {
        this.paymentGateway = paymentGateway;
    }

    @Transactional
    public String sendPayout(String merchantId, Money amount) {
        Money limit = this.paymentGateway.fetchDailyLimit(merchantId);
        if (amount.isGreaterThan(limit)) {
            throw new PayoutLimitExceededException(merchantId, amount, limit);
        }
        String reference = this.paymentGateway.sendPayout(merchantId, amount);
        log.debug("Payout {} accepted for merchant {} ({})", reference, merchantId, amount);
        return reference;
    }
}
