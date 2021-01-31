import { Component, OnInit } from '@angular/core';
import { Contract } from '../contract';
import { ContractService } from '../contract.service';
import { MessageService } from '../message.service';

@Component({
  selector: 'app-contracts',
  templateUrl: './contracts.component.html',
  styleUrls: ['./contracts.component.css']
})
export class ContractsComponent implements OnInit {

  contracts: Contract[];

  getContracts(): void {
    this.contractService.getContracts()
      .subscribe(contracts => {this.contracts = contracts; console.log(contracts);});
  }

  constructor(private contractService: ContractService) { }

  ngOnInit(): void {
    this.getContracts();
  }

}
