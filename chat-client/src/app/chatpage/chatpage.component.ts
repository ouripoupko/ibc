import { Component, OnInit } from '@angular/core';
import { ContractService } from '../contract.service';
import { Statement } from '../statement'
import { Method } from '../contract';

@Component({
  selector: 'app-chatpage',
  templateUrl: './chatpage.component.html',
  styleUrls: ['./chatpage.component.css']
})
export class ChatpageComponent implements OnInit {

  id: string;
  title: string;
  counter: number = 0;

  constructor(
    private contractService: ContractService,
  ) {}

  ngOnInit(): void {
    this.id = '';
    this.title = 'Topics';
    this.contractService.listen().addEventListener('message', message => {
      this.counter = this.counter + 1;
    });
  }
}
