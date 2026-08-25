// n8n Code node: turn /api/check-new-bills alerts into email items.
const body = $json;
if (!body.success || !body.alerts_count) return [];

function esc(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

const items = [];
for (const a of (body.alerts || [])) {
  const isStatus = a.alert_type === 'status_update';
  const banner = isStatus
    ? '<p style="display:inline-block;background:#fef3c7;border:1px solid #f59e0b;color:#92400e;font-size:13px;font-weight:700;padding:6px 12px;border-radius:999px;margin:0 0 14px;">Status updated: ' + esc(a.previous_status) + ' &rarr; ' + esc(a.bill_status) + '</p>'
    : '<p style="display:inline-block;background:#ecfdf5;border:1px solid #10b981;color:#065f46;font-size:13px;font-weight:700;padding:6px 12px;border-radius:999px;margin:0 0 14px;">New bill matching: ' + esc((a.matched_keywords || []).join(', ')) + '</p>';
  const summaryHtml = esc(a.summary).replace(/\n/g, '<br>');
  const html = '<div style="max-width:640px;margin:0 auto;font-family:Arial,sans-serif;">'
    + '<div style="text-align:center;margin-bottom:20px;"><span style="display:inline-block;background:#7c3aed;color:#fff;border-radius:12px;padding:10px 16px;font-size:18px;font-weight:700;">VidhanAI</span></div>'
    + '<div style="background:#ffffff;border-radius:16px;padding:28px;border:1px solid #e2e8f0;">'
    + banner
    + '<h1 style="margin:0 0 6px;color:#0f172a;font-size:20px;">' + esc(a.bill_title) + '</h1>'
    + '<p style="margin:0 0 14px;color:#64748b;font-size:13px;">Ministry of ' + esc(a.bill_ministry) + ' &bull; Status: ' + esc(a.bill_status) + '</p>'
    + '<div style="color:#334155;font-size:14px;line-height:1.65;">' + summaryHtml + '</div>'
    + (a.bill_url ? '<p style="margin:14px 0 0;"><a href="' + a.bill_url + '" style="color:#7c3aed;font-weight:600;">Read the full bill on PRS India</a></p>' : '')
    + '<hr style="border:none;border-top:1px solid #e2e8f0;margin:22px 0;">'
    + '<p style="margin:0;color:#94a3b8;font-size:12px;">AI-generated summary - may contain errors. Unsubscribe by replying to this email.</p>'
    + '</div></div>';
  const subject = isStatus
    ? 'Update on a bill you track: ' + a.bill_title
    : 'New bill for you: ' + a.bill_title;
  items.push({ json: { email: a.email, subject, html, notification_id: a.notification_id } });
}
return items;
