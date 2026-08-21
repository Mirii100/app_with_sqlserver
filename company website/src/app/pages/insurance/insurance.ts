import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-insurance',
  imports: [CommonModule, RouterLink],
  templateUrl: './insurance.html',
  styleUrl: './insurance.scss',
})
export class Insurance {
  covers = [
    {
      icon: 'fa-solid fa-heart-pulse',
      name: 'Life Cover',
      desc: 'Comprehensive life protection from KSh 1,500/month, with instant payouts to your nominated beneficiaries.',
    },
    {
      icon: 'fa-solid fa-hands-holding-circle',
      name: 'Funeral Cover',
      desc: 'Cover for you and up to 8 family members with payouts within 24 hours — because families need certainty.',
    },
    {
      icon: 'fa-solid fa-car',
      name: 'Asset & Motor',
      desc: 'Comprehensive motor, home and electronics cover with free valuation and same-day claim assessment.',
    },
    {
      icon: 'fa-solid fa-store',
      name: 'Business Insurance',
      desc: 'Protect stock, premises and liability exposure for SMEs, chama projects and agri-business ventures.',
    },
    {
      icon: 'fa-solid fa-plane',
      name: 'Travel Insurance',
      desc: 'Medical, baggage and trip-cancellation cover for diaspora members and frequent travellers.',
    },
    {
      icon: 'fa-solid fa-briefcase-medical',
      name: 'Health Cover',
      desc: 'Inpatient and outpatient plans with access to 400+ hospitals countrywide starting from KSh 2,900/month.',
    },
  ];

  promises = [
    { icon: 'fa-solid fa-bolt', text: 'Claims settled in as little as 24 hours' },
    { icon: 'fa-solid fa-file-shield', text: 'Simple paperwork — most claims need only ID + claim form' },
    { icon: 'fa-solid fa-phone-volume', text: 'Dedicated claims line open 24/7' },
  ];
}
