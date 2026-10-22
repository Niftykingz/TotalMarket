# Integration into existing TotalMarket frontend

The source-preserving logo component is in `graphics/company-logo.js` and display CSS in `graphics/logo-display.css`.

Only pass an `approvedLogoUrl` after rights review and after the company-to-logo identity mapping is verified. If none is supplied, a neutral initials tile appears. Never display a mock or AI-generated company mark as an official logo.

Example:
```js
import { createCompanyLogo } from './company-logo.js';
const node = createCompanyLogo({ companyName: 'Example Limited', symbol: 'EXAMPLE', approvedLogoUrl: null });
document.querySelector('#company-logo-slot').append(node);
```

This is a standalone integration module. It is not wired into live article cards because the production frontend component structure has not yet been confirmed.

Source review update (22 Oct 2026): TCS media kit lists logo downloads and editorial imagery, but its general legal disclaimer restricts commercial redistribution; NVIDIA expressly requires written authorization for logo use. Both remain pending review. Links are in `data/logo-source-queue.json`.
