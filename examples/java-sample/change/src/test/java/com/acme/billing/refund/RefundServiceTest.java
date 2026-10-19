package com.acme.billing.refund;

import org.junit.jupiter.api.Test;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.is;

class RefundServiceTest {

    @Test
    void test1() {
        assertThat(new DefaultRefundPolicy().isRefundable("inv-1"), is(true));
    }
}
