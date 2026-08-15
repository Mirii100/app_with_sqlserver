import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface Job {
  title: string;
  department: string;
  location: string;
  type: string;
}

@Component({
  selector: 'app-careers',
  imports: [CommonModule, RouterLink],
  templateUrl: './careers.html',
  styleUrl: './careers.scss',
})
export class Careers {
  perks = [
    { icon: 'fa-solid fa-graduation-cap', title: 'Learning & growth', desc: 'Annual training budgets, certifications and mentorship.' },
    { icon: 'fa-solid fa-heart-pulse', title: 'Health & wellness', desc: 'Comprehensive medical cover and wellness programs.' },
    { icon: 'fa-solid fa-piggy-bank', title: 'Member benefits', desc: 'Competitive staff savings and loan schemes.' },
    { icon: 'fa-solid fa-house-circle-check', title: 'Work-life balance', desc: 'Flexible working arrangements and generous leave.' },
  ];

  jobs: Job[] = [
    { title: 'Relationship Manager', department: 'Retail Banking', location: 'Nairobi', type: 'Full-time' },
    { title: 'Digital Product Manager', department: 'Digital Banking', location: 'Nairobi', type: 'Full-time' },
    { title: 'Credit Analyst', department: 'Credit & Risk', location: 'Nairobi', type: 'Full-time' },
    { title: 'Branch Sales Officer', department: 'Retail Banking', location: 'Mombasa', type: 'Full-time' },
    { title: 'Mobile App Developer', department: 'Technology', location: 'Hybrid', type: 'Full-time' },
    { title: 'Customer Support Associate', department: 'Operations', location: 'Kisumu', type: 'Contract' },
  ];
}
