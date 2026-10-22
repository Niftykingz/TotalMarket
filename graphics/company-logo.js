/* TotalMarket logo display: preserve source aspect ratio and bytes. */
export function createCompanyLogo({ companyName, symbol, approvedLogoUrl, alt } = {}) {
  const holder = document.createElement('span');
  holder.className = 'tm-company-logo tm-company-logo--card';
  holder.setAttribute('aria-label', companyName || symbol || 'Company');
  if (approvedLogoUrl && /^(\/|https:\/\/)/.test(approvedLogoUrl)) {
    const img = document.createElement('img');
    img.src = approvedLogoUrl;
    img.alt = alt || (companyName ? companyName + ' logo' : 'Company logo');
    img.loading = 'lazy';
    img.decoding = 'async';
    img.addEventListener('error', () => {
      holder.replaceChildren(createPlaceholder(companyName, symbol));
    }, { once: true });
    holder.append(img);
  } else {
    holder.append(createPlaceholder(companyName, symbol));
  }
  return holder;
}
function createPlaceholder(companyName, symbol) {
  const el = document.createElement('span');
  el.className = 'tm-logo-placeholder';
  el.textContent = (symbol || companyName || '?').slice(0, 2).toUpperCase();
  el.setAttribute('aria-hidden', 'true');
  return el;
}
