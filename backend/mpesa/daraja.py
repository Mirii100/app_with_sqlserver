"""Daraja API client for Safaricom M-Pesa STK Push.

Implements the three-step flow:
  1. Authenticate – exchange consumer key/secret for an OAuth bearer token.
  2. STK Push  – request the customer's phone to approve a payment
     (Buy Goods till or Paybill).
  3. Query     – poll the checkout request status until the customer
     completes / cancels the STK prompt.

All HTTP calls go through :mod:`urllib` so the package has no extra
dependencies beyond ``requests`` (already used by the project).
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.conf import settings

logger = logging.getLogger(__name__)


class DarajaAPIError(Exception):
    """Raised when the Daraja API returns an error."""

    def __init__(self, message, status_code=None, raw_response=None):
        super().__init__(message)
        self.status_code = status_code
        self.raw_response = raw_response


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _is_sandbox():
    return getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox').lower() == 'sandbox'


def _base_url():
    return (
        'https://sandbox.safaricom.co.ke' if _is_sandbox()
        else 'https://api.safaricom.co.ke'
    )


def _auth_url():
    return f'{_base_url()}/oauth/v1/generate?grant_type=client_credentials'


def _stk_push_url():
    return f'{_base_url()}/mpesa/stkpush/v1/processrequest'


def _stk_query_url():
    return f'{_base_url()}/mpesa/stkpush/v1/query'


def _make_request(url, payload, timeout=30):
    """POST *payload* (dict) to *url* as JSON and return the decoded body."""
    data = json.dumps(payload).encode('utf-8')
    req = Request(
        url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8')
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {}
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        raise DarajaAPIError(
            f'Daraja API error: {exc.code} {exc.reason}',
            status_code=exc.code,
            raw_response=body,
        )
    except URLError as exc:
        raise DarajaAPIError(
            f'Network error contacting Daraja API: {exc.reason}',
        )


# ---------------------------------------------------------------------------
# Password / timestamp
# ---------------------------------------------------------------------------

def _generate_timestamp():
    """Return a Daraja-compatible timestamp: ``YYYYMMDDHHMMSS``."""
    return datetime.now().strftime('%Y%m%d%H%M%S')


def _generate_stk_password(shortcode, passkey, timestamp):
    """Build the base64-encoded STK Push password.

    The password is ``base64(ShortCode + PassKey + Timestamp)``.
    """
    raw = f'{shortcode}{passkey}{timestamp}'
    return base64.b64encode(raw.encode('utf-8')).decode('utf-8')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_access_token():
    """Exchange the consumer key/secret for an OAuth bearer token.

    Returns the token string on success or raises :class:`DarajaAPIError`.
    """
    consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
    consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
    if not consumer_key or not consumer_secret:
        raise DarajaAPIError(
            'MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be set in env.'
        )

    import base64 as b64
    credentials = b64.b64encode(
        f'{consumer_key}:{consumer_secret}'.encode('utf-8')
    ).decode('utf-8')

    req = Request(
        _auth_url(),
        headers={
            'Authorization': f'Basic {credentials}',
            'Accept': 'application/json',
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except HTTPError as exc:
        raise DarajaAPIError(
            f'Auth failed: {exc.code}',
            status_code=exc.code,
        )
    except URLError as exc:
        raise DarajaAPIError(
            f'Network error during auth: {exc.reason}',
        )

    if 'access_token' not in body:
        logger.error('Unexpected auth response: %s', body)
        raise DarajaAPIError(
            f'Unexpected auth response: {body}',
        )

    token = body['access_token']
    expires_in = body.get('expires_in', 3600)  # default 1 hour
    logger.info('Obtained Daraja access token (len=%s, expires in %ss)',
                len(token), expires_in)
    return token


def send_stk_push(
    phone_number,
    amount,
    item_type,
    item_id,
    account_reference=None,
    transaction_desc='Alexia wallet top-up',
    callback_url=None,
    passkey=None,
    shortcode=None,
    party_b=None,
):
    """Initiate an STK Push request.

    Parameters
    ----------
    phone_number : str
        Recipient phone number in international format (e.g. ``254712345678``).
    amount : int or Decimal
        Amount to charge.
    item_type : str
        Either ``'buy_goods'`` (Buy Goods) or ``'paybill'`` (Paybill).
    item_id : str
        Till number (for Buy Goods) or Paybill number (for Paybill).
    account_reference : str, optional
        Account reference – required for Paybill.
    transaction_desc : str
        Human-readable description shown on the STK screen.
    callback_url : str, optional
        Override the configured callback URL.
    passkey : str, optional
        Override the configured passkey (sandbox/live).
    shortcode : str, optional
        Override the configured business short code.
    party_b : str, optional
        Override PartyB (till/paybill).  When ``item_id`` is a phone number
        (person-to-person), this defaults to ``shortcode``.

    Returns
    -------
    dict
        The raw Daraja response payload.
    """
    # Resolve configuration from Django settings
    shortcode = shortcode or getattr(settings, 'MPESA_SHORTCODE', '')
    passkey = passkey or getattr(settings, 'MPESA_PASSKEY', '')
    callback_url = callback_url or getattr(
        settings, 'MPESA_CALLBACK_URL',
        'https://yourdomain.com/mpesa/callback/',
    )

    if not shortcode or not passkey:
        raise DarajaAPIError(
            'MPESA_SHORTCODE and MPESA_PASSKEY must be set in env.'
        )

    # Normalise phone number to 254XXXXXXXXX
    phone = phone_number.strip().replace(' ', '').replace('+', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    if not phone.startswith('254'):
        raise DarajaAPIError(
            f'Phone number must be Kenyan (254...): {phone}'
        )

    # Choose transaction type
    # Both 'buy_goods' and 'buy_goods_services' use CustomerBuyGoodsPayBillMode
    # in the Daraja API. The distinction is only for ledger categorisation.
    if item_type in ('buy_goods', 'buy_goods_services'):
        txn_type = 'CustomerBuyGoodsPayBillMode'
    elif item_type == 'paybill':
        txn_type = 'CustomerPayBillPaybillMode'
    else:
        raise DarajaAPIError(
            f"item_type must be 'buy_goods', 'buy_goods_services' or 'paybill', "
            f"got '{item_type}'"
        )

    # If PartyB was not explicitly provided, check whether item_id looks like
    # a phone number (person-to-person top-up) and fall back to shortcode.
    if party_b is None:
        stripped = item_id.strip()
        if stripped.startswith('254') or stripped.startswith('07') or stripped.startswith('01'):
            party_b = shortcode
        else:
            party_b = item_id

    timestamp = _generate_timestamp()
    password = _generate_stk_password(shortcode, passkey, timestamp)

    token = get_access_token()

    payload = {
        'BusinessShortCode': shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': txn_type,
        'CallBackURL': callback_url,
        'PartyA': phone,
        'Amount': str(amount),
        'PartyB': party_b,
        'AccountReference': account_reference or 'AlexiaFinancials',
        'PhoneNumber': phone,
        'TransactionDesc': transaction_desc,
    }

    logger.debug('Daraja STK Push payload: %s', payload)

    req = Request(
        _stk_push_url(),
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        logger.error(
            'STK Push HTTP %d: request=%s response=%s',
            exc.code, payload, body[:500],
        )
        raise DarajaAPIError(
            f'STK Push failed: {exc.code} {exc.reason}',
            status_code=exc.code,
            raw_response=body,
        )
    except URLError as exc:
        raise DarajaAPIError(
            f'Network error during STK Push: {exc.reason}',
        )

    logger.info(
        'STK Push sent for %s, CheckoutRequestID=%s',
        phone,
        body.get('CheckoutRequestID', 'N/A'),
    )
    return body


def query_stk_status(checkout_request_id):
    """Query the status of an STK Push request by its CheckoutRequestID."""
    token = get_access_token()
    shortcode = getattr(settings, 'MPESA_SHORTCODE', '')
    passkey = getattr(settings, 'MPESA_PASSKEY', '')

    timestamp = _generate_timestamp()
    password = _generate_stk_password(shortcode, passkey, timestamp)

    payload = {
        'BusinessShortCode': shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id,
    }

    req = Request(
        _stk_query_url(),
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        },
        method='POST',
    )

    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        raise DarajaAPIError(
            f'STK Query failed: {exc.code} {exc.reason}',
            status_code=exc.code,
            raw_response=body,
        )

    return body
