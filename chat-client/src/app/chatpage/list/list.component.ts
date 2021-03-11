import { Component, OnInit, Input } from '@angular/core';
import { Page } from '../../statement';
import { Method } from '../../contract';
import { FormControl } from '@angular/forms';
import { MatInput } from '@angular/material/input';
import { ContractService } from '../../contract.service';
import {CdkDragDrop, moveItemInArray} from '@angular/cdk/drag-drop';

@Component({
  selector: 'app-list',
  templateUrl: './list.component.html',
  styleUrls: ['./list.component.css']
})
export class ListComponent implements OnInit {

  @Input() sid: number;
  @Input() name: string;
  page: Page;
  newItem: boolean;
  statementForm: FormControl = new FormControl();

  constructor( private contractService: ContractService ) { }

  ngOnInit(): void {
    this.newItem = false;
    this.getStatements();
  }


  submit() {
    this.newItem = false;
    this.createStatement(this.statementForm.value);
    this.statementForm.setValue("");
  }

  createStatement(statement): void {
    const method = this.page.parent ? { name: 'reply', values: [this.page.parent.me, statement, 'not now please']} as Method :
                                        { name: 'create_topic', values: [statement]} as Method;
    const id = this.page.parent ? this.page.parent.me : 0;
    this.contractService.createStatement(this.name, method)
      .subscribe();
    this.contractService.getStatements(this.name, { name: 'get_page', values: [id]} as Method)
      .subscribe(page => this.page = page);

  }
  getStatements(): void {
    this.contractService.getStatements(this.name, { name: 'get_page', values: [this.sid]} as Method)
      .subscribe(page => this.page = page );

  }

  drop(event: CdkDragDrop<string[]>) {
    moveItemInArray(this.page.kids, event.previousIndex, event.currentIndex);
  }
}
