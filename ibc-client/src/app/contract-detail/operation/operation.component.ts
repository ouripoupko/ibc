import { Component, OnChanges, Input, Output, EventEmitter } from '@angular/core';

import { ContractService } from '../../contract.service';
import { Contract, Method } from '../../contract';

@Component({
  selector: 'app-operation',
  templateUrl: './operation.component.html',
  styleUrls: ['./operation.component.css']
})
export class OperationComponent implements OnChanges {

  constructor(
    private contractService: ContractService
  ) { }

  @Input() agent: string;
  @Input() name: string;
  @Input() method: string;
  @Input() arguments: string[];

  values: string[];

  @Output() updateContractEvent = new EventEmitter<Contract>();

  ngOnChanges(): void {
    this.values = new Array(this.arguments.length);
  }

  call(): void {
    let val_dict = {};
    for(let i in this.arguments) {
      val_dict[this.arguments[i]] = this.values[i] ? JSON.parse(this.values[i]) : null;
    }
    console.log(val_dict);
    this.contractService.callContract( this.agent, this.name, this.method, {values: val_dict} as Method)
      .subscribe(contract => this.updateContractEvent.emit(contract));
  }
}
