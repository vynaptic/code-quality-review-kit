package com.acme.billing.util;

import com.acme.billing.refund.RefundService.RefundStatus;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.text.SimpleDateFormat;
import java.util.Date;

public class PaymentUtils {

    private static final SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd");
    private static final HttpClient CLIENT = HttpClient.newHttpClient();

    public static String callProvider(String path, String invoiceId, double amount) {
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create("https://api.stripe.com" + path))
                    .POST(HttpRequest.BodyPublishers.ofString("{\"invoice\":\"" + invoiceId + "\",\"amount\":" + amount + "}"))
                    .build();
            return CLIENT.send(request, HttpResponse.BodyHandlers.ofString()).body();
        }
        catch (Exception e) {
            throw new RuntimeException(e.getMessage());
        }
    }

    public static RefundStatus parseStatus(String raw) {
        if (raw.contains("done")) {
            return RefundStatus.DONE;
        }
        else if (raw.contains("failed")) {
            return RefundStatus.FAILED;
        }
        return RefundStatus.PENDING;
    }

    public static String formatDate(Date date) {
        return DATE_FORMAT.format(date);
    }

    public static boolean checkAmount(double amount) {
        return amount > 0;
    }
}
