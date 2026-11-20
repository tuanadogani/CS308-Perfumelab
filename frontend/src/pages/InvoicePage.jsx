import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { getInvoice, getInvoicePdf } from '../api/checkoutApi';
import { formatPrice } from '../utils/format';
import '../styles/checkout.css';

// Requirement 4: after the bank confirms the payment, the invoice is shown on the screen
// (and a PDF copy has been emailed). The PDF needs the login token, so it is fetched as a
// blob and offered through a local blob: link.
export default function InvoicePage() {
  const { id } = useParams();
  const justPaid = useLocation().state?.justPaid;
  const [invoice, setInvoice] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    let objectUrl = null;
    getInvoice(id)
      .then((data) => { if (!cancelled) setInvoice(data); })
      .catch((err) => { if (!cancelled) setError(err.status === 404 ? 'Invoice not found.' : err.message); });
    getInvoicePdf(id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPdfUrl(objectUrl);
      })
      .catch(() => { /* the on-screen invoice still works without the PDF link */ });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  if (error) {
    return (
      <div className="container section empty">
        <h2>{error}</h2>
        <Link to="/shop" className="btn btn-dark">Go to collection</Link>
      </div>
    );
  }
  if (!invoice) return <div className="container section"><p className="muted">Loading invoice…</p></div>;

  return (
    <div className="container section invoice">
      {justPaid && (
        <p className="form-success" role="status">
          Payment confirmed — thank you! A PDF copy of this invoice was sent to <strong>{invoice.customerEmail}</strong>.
        </p>
      )}
      <div className="invoice__card">
        <div className="invoice__head">
          <div>
            <p className="eyebrow">PerfumeLab</p>
            <h1>Invoice {invoice.number}</h1>
          </div>
          <div className="invoice__meta muted small">
            <span>Order #{invoice.orderId}</span>
            <span>{new Date(invoice.issuedAt).toLocaleString()}</span>
          </div>
        </div>

        <div className="invoice__parties">
          <div><p className="eyebrow">Billed to</p><p>{invoice.customerName}<br />{invoice.customerEmail}</p></div>
          <div><p className="eyebrow">Delivery address</p><p>{invoice.shippingAddress}</p></div>
          <div><p className="eyebrow">Payment</p><p>Card ending {invoice.cardLast4 || '----'}</p></div>
        </div>

        <table className="invoice__table">
          <thead>
            <tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Total</th></tr>
          </thead>
          <tbody>
            {invoice.items.map((line) => (
              <tr key={line.productId}>
                <td>{line.brand} {line.name} <span className="muted">{line.volumeMl} ml</span></td>
                <td>{line.quantity}</td>
                <td>{formatPrice(line.unitPrice)}</td>
                <td>{formatPrice(line.lineTotal)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr><td colSpan={3}>Total</td><td>{formatPrice(invoice.total)}</td></tr>
          </tfoot>
        </table>

        <div className="invoice__actions">
          {pdfUrl ? (
            <>
              <a className="btn btn-dark" href={pdfUrl} target="_blank" rel="noreferrer">Open PDF</a>
              <a className="btn btn-ghost" href={pdfUrl} download={`${invoice.number}.pdf`}>Download PDF</a>
            </>
          ) : <span className="muted small">Preparing PDF…</span>}
          <Link className="btn btn-ghost" to="/shop">Continue shopping</Link>
        </div>
      </div>
    </div>
  );
}
