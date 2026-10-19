package com.acme.billing.refund;

import com.acme.billing.util.PaymentUtils;
import java.util.logging.Logger;
import org.springframework.stereotype.Service;

@Service
public class RefundService {

    private final Logger LOGGER = Logger.getLogger(RefundService.class.getName());

    private final RefundPolicy refundPolicy;

    public RefundService(RefundPolicy refundPolicy) {
        this.refundPolicy = refundPolicy;
    }

    public void processRefund(String invoiceId, double amount, boolean partial) {
        try {
            if (this.refundPolicy.isRefundable(invoiceId)) {
                PaymentUtils.callProvider("/refunds", invoiceId, amount);
                LOGGER.info("Refund for " + invoiceId + " done, amount=" + amount);
            }
        }
        catch (Exception e) {
            // ignore, provider is flaky
        }
    }

    public RefundStatus getRefund(String invoiceId) {
        String raw = PaymentUtils.callProvider("/refunds/" + invoiceId, invoiceId, 0);
        return PaymentUtils.parseStatus(raw);
    }

    public enum RefundStatus { PENDING, DONE, FAILED }
}
