import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface FaqItem {
  q: string;
  a: string;
}

interface FaqCategory {
  name: string;
  icon: string;
  items: FaqItem[];
}

@Component({
  selector: 'app-faq',
  imports: [CommonModule, RouterLink],
  templateUrl: './faq.html',
  styleUrl: './faq.scss',
})
export class Faq {
  openIndex: number = 0;

  categories: FaqCategory[] = [
    {
      name: 'Accounts',
      icon: 'fa-solid fa-wallet',
      items: [
        {
          q: 'How do I open an account?',
          a: 'Open an account online in under 5 minutes, through the Alexia-Pesa app, or at any of our branches. You need a valid national ID or passport, and a passport-size photo. Online applications are approved instantly.',
        },
        {
          q: 'What is the minimum balance?',
          a: 'Our Everyday Savings Account has no minimum opening balance. A minimum of KSh 500 is required to earn interest, and there are no monthly ledger fees.',
        },
        {
          q: 'How do I get my bank statement?',
          a: 'Statements are available free of charge in the app (download as PDF) or via email. You can also request printed statements at any branch.',
        },
      ],
    },
    {
      name: 'Loans',
      icon: 'fa-solid fa-sack-dollar',
      items: [
        {
          q: 'How long does loan approval take?',
          a: 'Most applications are assessed and approved within 24–48 hours. Salary advances can be approved instantly for members with active salary agreements.',
        },
        {
          q: 'How do I repay my loan?',
          a: 'Repayment is automatically deducted from your account on agreed dates, or you can repay manually via M-Pesa or at any branch. There is no penalty for early settlement.',
        },
        {
          q: 'Can I borrow if I am not yet a member?',
          a: 'No. You must be an active member with at least 3 months of regular savings history to qualify for credit.',
        },
      ],
    },
    {
      name: 'Chama & Groups',
      icon: 'fa-solid fa-people-group',
      items: [
        {
          q: 'How does the Chama Collective Account work?',
          a: 'Open a group account with a minimum of 5 members. The group contributes regularly, earns interest, and can access group loans of up to 3x its savings. A group register with authorised signatories is required.',
        },
        {
          q: 'Who manages the group account?',
          a: 'The group appoints at least three authorised signatories (chair, treasurer, secretary). All withdrawals require two signatories and a group resolution.',
        },
      ],
    },
    {
      name: 'Diaspora & Remittances',
      icon: 'fa-solid fa-earth-africa',
      items: [
        {
          q: 'Can I open an account from abroad?',
          a: 'Yes. Diaspora accounts can be opened online using your passport or foreign national ID. Our team supports video verification for customers outside Kenya.',
        },
        {
          q: 'How long do remittances take?',
          a: 'International remittances are credited within minutes to 24 hours, depending on the sending provider. A 1.5% fee applies (min KSh 250, max KSh 5,000).',
        },
      ],
    },
    {
      name: 'Mobile Banking',
      icon: 'fa-solid fa-mobile-screen-button',
      items: [
        {
          q: 'How do I download the Alexia-Pesa app?',
          a: 'Search "Alexia-Pesa" on the App Store or Google Play Store, or download it from the links at the bottom of this website. It is free to download.',
        },
        {
          q: 'What can I do in the app?',
          a: 'You can check balances, send money, pay bills, buy airtime, deposit and withdraw via M-Pesa, apply for loans, set savings goals, and view statements.',
        },
        {
          q: 'What is the USSD code?',
          a: 'Dial *571# on any mobile network to access balances, transfers and airtime purchases without data or a smartphone.',
        },
      ],
    },
  ];

  trackByIndex(index: number): number {
    return index;
  }
}
