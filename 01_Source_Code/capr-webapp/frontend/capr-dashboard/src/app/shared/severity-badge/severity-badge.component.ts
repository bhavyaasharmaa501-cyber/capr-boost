import { Component, input } from '@angular/core';

@Component({
  selector: 'app-severity-badge',
  standalone: true,
  template: `<span class="badge" [class]="'sev-' + severity().toLowerCase()">{{ severity() }}</span>`,
  styles: [
    `
      .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        color: white;
        white-space: nowrap;
      }
      .sev-low {
        background: #607d8b;
      }
      .sev-medium {
        background: #f9a825;
        color: rgba(0, 0, 0, 0.87);
      }
      .sev-high {
        background: #ef6c00;
      }
      .sev-critical {
        background: #c62828;
      }
    `,
  ],
})
export class SeverityBadgeComponent {
  readonly severity = input.required<string>();
}
