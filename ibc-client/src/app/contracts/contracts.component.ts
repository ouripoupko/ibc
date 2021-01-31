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

  add(name: string): void {
    name = name.trim();
    if (!name) { return; }
    this.contractService.addContract({ name } as Contract)
      .subscribe(contract => {
        this.contracts.push(contract);
      });
  }

  constructor(private contractService: ContractService) { }

  ngOnInit(): void {
    this.getContracts();
  }

}
