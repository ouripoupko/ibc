import { Component, OnInit } from '@angular/core';
import { ContractService } from '../contract.service';

@Component({
  selector: 'app-chatpage',
  templateUrl: './chatpage.component.html',
  styleUrls: ['./chatpage.component.css']
})
export class ChatpageComponent implements OnInit {

  id: number;
  title: string;

  constructor(
    private contractService: ContractService,
  ) {}

  ngOnInit(): void {
    this.id = 0;
    this.title = 'Topics';
  }
}
