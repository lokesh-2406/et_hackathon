"""
create_test_pdf.py — Synthetic CAMS-style PDF generator
Generates a golden portfolio PDF that the Parser regex can read reliably.

Usage:
    # Default golden portfolio (8 funds, age 32, SIP 15000):
    python create_test_pdf.py

    # Custom portfolio:
    python create_test_pdf.py --output data/samples/my_test.pdf --age 45 --sip 25000 \
        --name "Rahul Sharma" --pan ABCDE1234F

    # Minimal single-fund test:
    python create_test_pdf.py --output data/samples/minimal.pdf --preset minimal
"""

import argparse
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# ---------------------------------------------------------------------------
# Fund definitions
# Each entry:
#   (scheme_name, isin, folio, sip_amount_per_month, start_date_str, nav_at_start)
#
# Scheme names are chosen to fuzzy-match the Kaggle CSVs via contains logic.
# The TXN_RE pattern requires amounts WITH a decimal point — use X.00 format.
# ---------------------------------------------------------------------------

GOLDEN_FUNDS = [
    {
        'scheme_name': 'HDFC Top 100 Fund - Regular Plan - Growth',
        'isin':        'INF179K01BE2',
        'folio':       '101/A1',
        'sip_amt':     10000.00,
        'start_date':  '15-Jan-2022',
        'start_nav':   480.00,
        'nav_now':     650.00,
    },
    {
        'scheme_name': 'Mirae Asset Large Cap Fund - Regular Plan - Growth',
        'isin':        'INF769K01018',
        'folio':       '202/B2',
        'sip_amt':     8000.00,
        'start_date':  '10-Mar-2022',
        'start_nav':   78.00,
        'nav_now':     98.00,
    },
    {
        'scheme_name': 'Axis Midcap Fund - Regular Plan - Growth',
        'isin':        'INF846K01198',
        'folio':       '303/C3',
        'sip_amt':     5000.00,
        'start_date':  '05-Jun-2022',
        'start_nav':   58.00,
        'nav_now':     68.00,
    },
    {
        'scheme_name': 'Parag Parikh Flexi Cap Fund - Regular Plan - Growth',
        'isin':        'INF789FB1X41',
        'folio':       '404/D4',
        'sip_amt':     15000.00,
        'start_date':  '01-Jan-2021',
        'start_nav':   38.00,
        'nav_now':     72.00,
    },
    {
        'scheme_name': 'SBI Small Cap Fund - Regular Plan - Growth',
        'isin':        'INF209K01V06',
        'folio':       '505/E5',
        'sip_amt':     3000.00,
        'start_date':  '20-Sep-2022',
        'start_nav':   112.00,
        'nav_now':     128.00,
    },
    {
        'scheme_name': 'ICICI Pru Bluechip Fund - Regular Plan - Growth',
        'isin':        'INF109K01AQ9',
        'folio':       '606/F6',
        'sip_amt':     4000.00,
        'start_date':  '12-Feb-2023',
        'start_nav':   64.00,
        'nav_now':     80.00,
    },
    {
        'scheme_name': 'Franklin India Prima Fund - Regular Plan - Growth',
        'isin':        'INF090I01HP5',
        'folio':       '707/G7',
        'sip_amt':     1500.00,
        'start_date':  '08-Aug-2023',
        'start_nav':   1650.00,
        'nav_now':     1820.00,
    },
    {
        'scheme_name': 'Kotak Debt Hybrid Fund - Regular Plan - Growth',
        'isin':        'INF174K01LS2',
        'folio':       '808/H8',
        'sip_amt':     2000.00,
        'start_date':  '01-Nov-2022',
        'start_nav':   38.00,
        'nav_now':     44.00,
    },
]

MINIMAL_FUNDS = [
    {
        'scheme_name': 'HDFC Top 100 Fund - Regular Plan - Growth',
        'isin':        'INF179K01BE2',
        'folio':       '101/A1',
        'sip_amt':     10000.00,
        'start_date':  '15-Jan-2023',
        'start_nav':   590.00,
        'nav_now':     650.00,
    },
    {
        'scheme_name': 'Parag Parikh Flexi Cap Fund - Regular Plan - Growth',
        'isin':        'INF789FB1X41',
        'folio':       '404/D4',
        'sip_amt':     5000.00,
        'start_date':  '15-Jan-2023',
        'start_nav':   60.00,
        'nav_now':     72.00,
    },
]

PRESETS = {
    'golden':  GOLDEN_FUNDS,
    'minimal': MINIMAL_FUNDS,
}


# ---------------------------------------------------------------------------
# Transaction generation
# ---------------------------------------------------------------------------

def _generate_monthly_sips(start_date_str: str, sip_amt: float,
                            start_nav: float, nav_now: float,
                            sip_day: int = 15) -> list[dict]:
    """
    Generate monthly SIP transactions from start_date to today.
    NAV interpolated linearly from start_nav to nav_now.
    Returns list of dicts with keys: date, type, amount, units, nav, balance.
    """
    fmt = '%d-%b-%Y'
    start = datetime.strptime(start_date_str, fmt).date()
    today = date.today()

    # Count total months
    delta = relativedelta(today, start)
    total_months = delta.years * 12 + delta.months + 1

    txns = []
    balance = 0.0

    for i in range(total_months):
        txn_date = start + relativedelta(months=i)
        txn_date = txn_date.replace(day=min(sip_day, 28))  # avoid month-end issues
        if txn_date > today:
            break

        # Linear NAV interpolation
        progress = i / max(total_months - 1, 1)
        nav = round(start_nav + (nav_now - start_nav) * progress, 4)

        units = round(sip_amt / nav, 3)
        balance = round(balance + units, 3)

        txns.append({
            'date':    txn_date.strftime(fmt),
            'type':    'SIP Purchase',
            'amount':  sip_amt,
            'units':   units,
            'nav':     nav,
            'balance': balance,
        })

    return txns


# ---------------------------------------------------------------------------
# PDF drawing helpers
# ---------------------------------------------------------------------------

COL_X = {
    'date':        55,
    'description': 135,
    'amount':      255,
    'units':       335,
    'nav':         415,
    'balance':     490,
}
PAGE_MARGIN = 50
TXN_ROW_H  = 13   # pixels per transaction row
FUND_HEADER_H = 95  # pixels for folio/scheme/ISIN/table-header block


def _draw_page_header(c, width, height, investor_name: str, pan: str,
                       email: str, period: str):
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(width / 2, height - 38, 'Consolidated Account Statement (CAS)')
    c.setFont('Helvetica', 9)
    c.drawString(PAGE_MARGIN, height - 56, f'Statement Period: {period}')
    c.drawString(PAGE_MARGIN, height - 69, f'Investor: {investor_name}')
    c.drawString(PAGE_MARGIN, height - 82, f'PAN: {pan} | Email: {email}')
    c.setLineWidth(0.8)
    c.line(PAGE_MARGIN, height - 90, width - PAGE_MARGIN, height - 90)


def _draw_table_header(c, y, width):
    c.setFillColor(colors.lightgrey)
    c.rect(PAGE_MARGIN, y - 13, width - 2 * PAGE_MARGIN, 14, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 7.5)
    for col, label in [('date', 'Date'), ('description', 'Description'),
                        ('amount', 'Amount (Rs)'), ('units', 'Units'),
                        ('nav', 'NAV'), ('balance', 'Balance Units')]:
        c.drawString(COL_X[col], y - 10, label)


def _draw_txn_row(c, y, txn: dict):
    c.setFont('Helvetica', 7.5)
    c.drawString(COL_X['date'],        y, txn['date'])
    c.drawString(COL_X['description'], y, txn['type'])
    # Format with exactly 2 decimal places — required for TXN_RE [\d,]+\.\d{2,}
    c.drawString(COL_X['amount'],  y, f"{txn['amount']:,.2f}")
    c.drawString(COL_X['units'],   y, f"{txn['units']:.3f}")
    c.drawString(COL_X['nav'],     y, f"{txn['nav']:.4f}")
    c.drawString(COL_X['balance'], y, f"{txn['balance']:.3f}")


def _draw_fund_block_header(c, y, fund: dict, width):
    """Draw Folio / Scheme / ISIN header for one fund block. Returns y after drawing."""
    c.setFont('Helvetica-Bold', 10)
    c.drawString(PAGE_MARGIN, y, f"Folio No: {fund['folio']}")

    c.setFont('Helvetica', 9)
    # CRITICAL: Parser SCHEME_RE looks for 'Scheme:' label
    c.drawString(PAGE_MARGIN, y - 14, f"Scheme: {fund['scheme_name']}")
    c.drawString(PAGE_MARGIN, y - 28, f"ISIN: {fund['isin']}")

    _draw_table_header(c, y - 40, width)
    return y - 56   # y position for first transaction row


# ---------------------------------------------------------------------------
# Main PDF generator
# ---------------------------------------------------------------------------

def create_portfolio_pdf(
    output_path:    str,
    funds:          list[dict],
    investor_name:  str = 'Devanshi Saxena',
    pan:            str = 'ABCDE1234F',
    email:          str = 'devanshi@hbtu.ac.in',
    sip_day:        int = 15,
) -> None:
    """
    Generate a CAMS-style PDF from a list of fund dicts.
    Each fund dict must have: scheme_name, isin, folio, sip_amt,
                              start_date, start_nav, nav_now.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    period = f"01-Jan-2021 to {date.today().strftime('%d-%b-%Y')}"
    _draw_page_header(c, width, height, investor_name, pan, email, period)

    curr_y = height - 110
    first_page = True

    for fund in funds:
        txns = _generate_monthly_sips(
            fund['start_date'], fund['sip_amt'],
            fund['start_nav'], fund['nav_now'], sip_day
        )
        if not txns:
            continue

        # Space needed: header block + all transaction rows + bottom margin
        needed = FUND_HEADER_H + len(txns) * TXN_ROW_H + 20

        # New page if not enough space
        if curr_y - needed < 60:
            c.showPage()
            curr_y = height - 50
            _draw_page_header(c, width, height, investor_name, pan, email, period)
            curr_y = height - 110

        # Draw fund header
        curr_y = _draw_fund_block_header(c, curr_y, fund, width)

        # Draw transactions
        for txn in txns:
            if curr_y < 60:
                c.showPage()
                curr_y = height - 50
                _draw_table_header(c, curr_y, width)
                curr_y -= 16

            _draw_txn_row(c, curr_y, txn)
            curr_y -= TXN_ROW_H

        # Closing balance line
        c.setFont('Helvetica-Bold', 8)
        c.drawString(PAGE_MARGIN, curr_y,
                     f"Closing Balance: {txns[-1]['balance']:.3f} units"
                     f"  |  Value @ NAV {fund['nav_now']}: "
                     f"Rs {txns[-1]['balance'] * fund['nav_now']:,.2f}")
        curr_y -= 20

        # Separator line
        c.setLineWidth(0.3)
        c.setStrokeColor(colors.grey)
        c.line(PAGE_MARGIN, curr_y, width - PAGE_MARGIN, curr_y)
        c.setStrokeColor(colors.black)
        curr_y -= 14

    # Footer
    c.setFont('Helvetica-Oblique', 7)
    c.drawCentredString(width / 2, 25, 'Generated by Portfolio Surgeon — Synthetic Test Artifact')
    c.save()
    print(f'[create_test_pdf] PDF created: {output_path}')
    print(f'  Funds    : {len(funds)}')
    print(f'  Investor : {investor_name} | PAN: {pan}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description='Portfolio Surgeon — Synthetic CAMS PDF Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--output',  default='data/samples/golden_portfolio.pdf',
                   help='Output PDF path (default: data/samples/golden_portfolio.pdf)')
    p.add_argument('--preset',  choices=['golden', 'minimal'], default='golden',
                   help='Fund preset to use (default: golden)')
    p.add_argument('--name',    default='Devanshi Saxena', help='Investor name')
    p.add_argument('--pan',     default='ABCDE1234F',      help='PAN number')
    p.add_argument('--email',   default='devanshi@hbtu.ac.in', help='Email')
    p.add_argument('--sip-day', type=int, default=15,
                   help='Day of month for SIP (default: 15)')
    p.add_argument('--age',     type=int, default=32,
                   help='Investor age — printed in summary (default: 32)')
    p.add_argument('--sip',     type=float, default=None,
                   help='Override all SIP amounts with a single value (optional)')
    return p.parse_args()


def main():
    args = parse_args()

    funds = [f.copy() for f in PRESETS[args.preset]]

    # Override all SIP amounts if --sip provided
    if args.sip:
        # Distribute proportionally based on original weights
        total_orig = sum(f['sip_amt'] for f in funds)
        for f in funds:
            f['sip_amt'] = round(args.sip * (f['sip_amt'] / total_orig), 2)

    create_portfolio_pdf(
        output_path=args.output,
        funds=funds,
        investor_name=args.name,
        pan=args.pan,
        email=args.email,
        sip_day=args.sip_day,
    )

    print(f'\n  Age      : {args.age} (pass this to main.py --age {args.age})')
    print(f'  Run with : python main.py --pdf {args.output} --age {args.age}')


if __name__ == '__main__':
    main()