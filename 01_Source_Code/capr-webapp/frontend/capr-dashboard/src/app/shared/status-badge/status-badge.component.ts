import { Component, input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `<span class="badge" [class]="'st-' + status().toLowerCase()">{{ status() }}</span>`,
  styles: [
    `
      .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        white-space: nowrap;
        background: #eceff1;
        color: rgba(0, 0, 0, 0.7);
      }
      .st-completed,
      .st-resolved {
        background: #2e7d32;
        color: white;
      }
      .st-failed,
      .st-falsepositive {
        background: #b71c1c;
        color: white;
      }
      .st-pending,
      .st-open {
        background: #1565c0;
        color: white;
      }
      .st-extracting,
      .st-predicting,
      .st-acknowledged {
        background: #f9a825;
        color: rgba(0, 0, 0, 0.87);
      }
    `,
  ],
})
export class StatusBadgeComponent {
  readonly status = input.required<string>();
}
