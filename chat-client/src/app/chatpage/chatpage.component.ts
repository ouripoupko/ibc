import { Component, OnInit } from '@angular/core';
import { ActivatedRoute,  Router} from '@angular/router';
import { Page } from '../statement';
import { Method } from '../contract';
import { ContractService } from '../contract.service';

@Component({
  selector: 'app-chatpage',
  templateUrl: './chatpage.component.html',
  styleUrls: ['./chatpage.component.css']
})
export class ChatpageComponent implements OnInit {
  page: Page;

  constructor(
    private route: ActivatedRoute,
    private contractService: ContractService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    if (this.contractService.getUrl()) {
      this.getStatements();
    } else {
      this.router.navigate(['/','connect'])
    }
  }

  getStatements(): void {
    const name = this.route.snapshot.paramMap.get('name');
    const id = +this.route.snapshot.paramMap.get('id');
    this.contractService.getStatements(name, { name: 'get_page', values: [id]} as Method)
      .subscribe(page => this.page = page);

  }
}
