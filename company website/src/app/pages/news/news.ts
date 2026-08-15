import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface NewsItem {
  title: string;
  excerpt: string;
  date: string;
  category: string;
  image: string;
  featured?: boolean;
}

@Component({
  selector: 'app-news',
  imports: [CommonModule, RouterLink],
  templateUrl: './news.html',
  styleUrl: './news.scss',
})
export class News {
  articles: NewsItem[] = [
    {
      title: 'Alexia Financials named SACCO of the Year 2026',
      excerpt: 'We are proud to announce that our members-first model has been recognised as Kenya’s SACCO of the Year at the 2026 Financial Services Excellence Awards.',
      date: 'July 12, 2026',
      category: 'Awards',
      image: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60',
      featured: true,
    },
    {
      title: 'New branch opens in Kisumu to serve the lakeside community',
      excerpt: 'Our fourth branch is now open on Oginga Odinga Street, bringing full banking, SME lending and remittance services to the region.',
      date: 'June 3, 2026',
      category: 'Expansion',
      image: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60',
    },
    {
      title: 'Alexia-Pesa app passes 1 million downloads',
      excerpt: 'A milestone moment for digital banking in Kenya — thanks to our members who bank with us every day from their phones.',
      date: 'May 19, 2026',
      category: 'Digital',
      image: 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60',
    },
    {
      title: 'Interest rates reduced on personal and chama loans',
      excerpt: 'Effective this quarter, personal loans are now available from 13.5% p.a. and chama group loans from 12.5% p.a. — putting more money back in members’ pockets.',
      date: 'April 2, 2026',
      category: 'Products',
      image: 'https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60',
    },
    {
      title: 'Financial literacy bootcamp returns for 2026',
      excerpt: 'Free budgeting, saving and investment workshops are coming to Nairobi, Mombasa and Kisumu. Spaces are limited — register early.',
      date: 'March 15, 2026',
      category: 'Community',
      image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60',
    },
    {
      title: 'Partnering with MSMEs for affordable asset finance',
      excerpt: 'Our new asset finance programme helps small businesses acquire vehicles and equipment with flexible terms and asset insurance included.',
      date: 'February 20, 2026',
      category: 'Partnerships',
      image: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60',
    },
  ];
}
