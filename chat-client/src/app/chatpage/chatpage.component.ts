import { Component, OnInit } from '@angular/core';
import { ActivatedRoute,  Router} from '@angular/router';
import { Page } from '../statement';
import { Contract, Method } from '../contract';
import { ContractService } from '../contract.service';

@Component({
  selector: 'app-chatpage',
  templateUrl: './chatpage.component.html',
  styleUrls: ['./chatpage.component.css']
})
export class ChatpageComponent implements OnInit {

  contracts: Contract[];
  page: Page;
  name: string;
  id: number;
  title: string;

  constructor(
    private route: ActivatedRoute,
    private contractService: ContractService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.name = this.route.snapshot.paramMap.get('name');
    this.id = +this.route.snapshot.paramMap.get('id');
    if (this.name) {
      this.title = 'Topics';
    } else {
      this.getContracts();
      this.title = 'Choose a contract';
    }
  }

  getContracts(): void {
    this.contractService.getContracts()
      .subscribe(contracts => this.contracts = contracts);
  }
}
