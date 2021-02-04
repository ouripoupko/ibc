import { Component, OnInit } from '@angular/core';
import { ContractService } from './contract.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {

  owner: string;
  title ='The Identity BlockChain';

  getIdentity(): void {
    this.contractService.getIdentity()
      .subscribe(name => this.owner = name);
  }

  constructor(private contractService: ContractService) { }

  ngOnInit(): void {
    this.getIdentity();
  }

}
