package com.acme.billing.payout;

import com.acme.billing.common.Money;

/** Port to the external payment provider; implemented by an adapter per provider. */
public interface PaymentGateway {

    /** Sends a payout and returns the provider's reference. */
    String sendPayout(String merchantId, Money amount);

    /** Fetches the current daily payout limit for a merchant (remote call). */
    Money fetchDailyLimit(String merchantId);
}
