import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface Leader {
  name: string;
  title: string;
  bio: string;
  initials: string;
}

interface Milestone {
  year: string;
  title: string;
  desc: string;
}

@Component({
  selector: 'app-about',
  imports: [CommonModule, RouterLink],
  templateUrl: './about.html',
  styleUrl: './about.scss',
})
export class About {
  values = [
    { icon: 'fa-solid fa-scale-balanced', name: 'Integrity', desc: 'We maintain the highest ethical standards in every transaction.' },
    { icon: 'fa-solid fa-lightbulb', name: 'Innovation', desc: 'Leveraging technology to make banking simpler, faster and safer.' },
    { icon: 'fa-solid fa-hand-holding-heart', name: 'Inclusion', desc: 'Financial services for everyone, everywhere — no one left behind.' },
    { icon: 'fa-solid fa-people-group', name: 'Member-first', desc: 'As a member-owned institution, your prosperity is our purpose.' },
  ];

  leaders: Leader[] = [
    { name: 'Alexander Mwangi', title: 'Chief Executive Officer', bio: 'Two decades of leadership across banking and fintech, championing inclusive digital finance across East Africa.', initials: 'AM' },
    { name: 'Grace Wanjiru', title: 'Chief Financial Officer', bio: 'Seasoned finance executive driving prudent asset management and sustainable member returns.', initials: 'GW' },
    { name: 'David Ochieng', title: 'Chief Risk Officer', bio: 'Expert in credit, compliance and enterprise risk with a track record of zero-tolerance fraud control.', initials: 'DO' },
  ];

  milestones: Milestone[] = [
    { year: '2010', title: 'Founded in Nairobi', desc: 'Alexia Financials begins as a small community SACCO serving 200 members.' },
    { year: '2014', title: 'First branch expansion', desc: 'Mombasa branch opens, and membership passes 50,000.' },
    { year: '2018', title: 'Digital leap', desc: 'Alexia-Pesa app and USSD (*571#) banking launch nationwide.' },
    { year: '2021', title: 'Licensed & KDIC-protected', desc: 'Full licensing with enhanced deposit protection for all members.' },
    { year: '2024', title: 'Diaspora banking', desc: 'Remote account opening and remittance services go live for Kenyans abroad.' },
    { year: '2026', title: 'SACCO of the Year', desc: 'Recognised nationally for excellence in member-centric financial services.' },
  ];
}
