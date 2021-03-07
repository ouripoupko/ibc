import { Component, OnInit } from '@angular/core';
import { ContractService } from '../contract.service';
import { Contract } from '../contract';
import { MatSliderModule } from '@angular/material/slider';

@Component({
  selector: 'app-connect',
  templateUrl: './connect.component.html',
  styleUrls: ['./connect.component.css']
})
export class ConnectComponent implements OnInit {
  title = 'Welcome to your new Democracy!';

  address: string;
  contracts: Contract[];

  constructor(private contractService: ContractService) { }

  connect(): void {
    this.contractService.getContracts(this.address)
      .subscribe(contracts => this.contracts = contracts);
  }

  ngOnInit(): void {
  }

}
